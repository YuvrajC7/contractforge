"""OpenAPI response compatibility and a bounded, non-executing AST codemod."""
import ast,copy,difflib,json


def response_schema(spec,path='/users',method='get'):
    try:return spec['paths'][path][method]['responses']['200']['content']['application/json']['schema']
    except (KeyError,TypeError):raise ValueError('Expected inline JSON object response at the selected operation')


def compare(old,new,path='/users',method='get'):
    a=response_schema(old,path,method);b=response_schema(new,path,method)
    if a.get('type')!='object' or b.get('type')!='object':raise ValueError('Only object responses supported')
    ap=a.get('properties',{});bp=b.get('properties',{});issues=[];renames={}
    for name,definition in bp.items():
        previous=definition.get('x-renamed-from')
        if previous:
            if previous not in ap or previous in bp or name in ap or previous in renames:
                raise ValueError('Ambiguous rename metadata')
            if definition.get('type')!=ap[previous].get('type'):
                issues.append({'kind':'type_change','field':previous,'repairable':False})
            else:
                renames[previous]=name;issues.append({'kind':'rename','from':previous,'to':name,'repairable':True})
    for name,definition in ap.items():
        if name not in bp and name not in renames:
            issues.append({'kind':'removed_field','field':name,'repairable':False})
        elif name in bp:
            if definition.get('type')!=bp[name].get('type'):
                issues.append({'kind':'type_change','field':name,'repairable':False})
            if 'enum' in bp[name] and set(bp[name]['enum'])!=set(definition.get('enum',[])):
                issues.append({'kind':'enum_change','field':name,'repairable':False})
    required_a=set(a.get('required',[]));required_b=set(b.get('required',[]))
    for field in required_a:
        if renames.get(field,field) not in required_b:
            issues.append({'kind':'required_guarantee_removed','field':field,'repairable':False})
    return {'issues':issues,'renames':renames}


def parse_client(source):
    if len(source)>10000:raise ValueError('Client too large')
    try:tree=ast.parse(source)
    except SyntaxError as e:raise ValueError('Invalid Python client') from e
    if len(tree.body)!=1 or not isinstance(tree.body[0],ast.FunctionDef):raise ValueError('One function required')
    f=tree.body[0]
    if (f.decorator_list or f.returns or f.args.defaults or f.args.vararg or f.args.kwarg or f.args.kwonlyargs
        or f.args.posonlyargs or len(f.args.args)!=1 or f.args.args[0].annotation
        or len(f.body)!=1 or not isinstance(f.body[0],ast.Return)):
        raise ValueError('Only a one-argument, single-return parser is supported')
    name=f.args.args[0].arg
    allowed=(ast.Module,ast.FunctionDef,ast.arguments,ast.arg,ast.Return,ast.Dict,ast.List,ast.Tuple,ast.Subscript,ast.Name,ast.Load,ast.Constant)
    for node in ast.walk(tree):
        if not isinstance(node,allowed):raise ValueError(f'Unsupported syntax: {type(node).__name__}')
        if isinstance(node,ast.Name) and node.id!=name:raise ValueError('Unknown name')
        if isinstance(node,ast.Constant) and not isinstance(node.value,(str,int,float,bool,type(None))):raise ValueError('Unsupported constant')
        if isinstance(node,ast.Dict) and any(k is None for k in node.keys):raise ValueError('Dictionary unpacking is not supported')
    return tree,name


def interpret(source,payload):
    """Evaluate only a pure projection subset. Never exec, eval, import, or spawn code."""
    tree,name=parse_client(source)
    def visit(node):
        if isinstance(node,ast.Constant):return node.value
        if isinstance(node,ast.Name):return payload
        if isinstance(node,ast.Dict):return {visit(k):visit(v) for k,v in zip(node.keys,node.values)}
        if isinstance(node,ast.List):return [visit(x) for x in node.elts]
        if isinstance(node,ast.Tuple):return tuple(visit(x) for x in node.elts)
        if isinstance(node,ast.Subscript):return visit(node.value)[visit(node.slice)]
        raise ValueError('Unsupported expression')
    return visit(tree.body[0].body[0].value)


def repair(source,old,new,path='/users',method='get'):
    tree,parameter=parse_client(source);diff=compare(old,new,path,method)
    if any(not i['repairable'] for i in diff['issues']):
        return {'status':'abstained','reason':'Change requires a human decision','analysis':diff,'source':source}
    changed=[]
    class Rename(ast.NodeTransformer):
        def visit_Subscript(self,node):
            self.generic_visit(node)
            if isinstance(node.value,ast.Name) and node.value.id==parameter and isinstance(node.slice,ast.Constant):
                oldkey=node.slice.value
                if oldkey in diff['renames']:
                    changed.append({'line':node.lineno,'from':oldkey,'to':diff['renames'][oldkey]})
                    node.slice=ast.copy_location(ast.Constant(diff['renames'][oldkey]),node.slice)
            return node
    fixed=ast.fix_missing_locations(Rename().visit(copy.deepcopy(tree)))
    candidate=ast.unparse(fixed)+'\n'
    parse_client(candidate)
    return {'status':'candidate' if changed else 'unchanged','source':candidate,'changes':changed,'analysis':diff,
      'patch':''.join(difflib.unified_diff(source.splitlines(True),candidate.splitlines(True),fromfile='client.py',tofile='client.py'))}


def validate_contract(source,cases):
    results=[]
    for case in cases:
        try:
            actual=interpret(source,case['response']);passed=actual==case['expected']
            results.append({'passed':passed,'actual':actual,'expected':case['expected']})
        except (ValueError,KeyError,TypeError,IndexError) as e:
            results.append({'passed':False,'error':type(e).__name__})
    return {'passed':sum(x['passed'] for x in results),'total':len(results),'results':results}


def spec(properties,required):
    return {'openapi':'3.0.3','info':{'title':'Fixture','version':'1'},'paths':{'/users':{'get':{'responses':{'200':{'description':'ok','content':{'application/json':{'schema':{'type':'object','properties':properties,'required':required}}}}}}}}}


def fixture(index=0,kind='rename'):
    oldkey=f'legacy_field_{index}';newkey=f'current_field_{index}'
    old=spec({oldkey:{'type':'string'},'active':{'type':'boolean'}},[oldkey,'active'])
    new=spec({newkey:{'type':'string','x-renamed-from':oldkey},'active':{'type':'boolean'}},[newkey,'active'])
    if kind=='type_change':new=spec({oldkey:{'type':'integer'},'active':{'type':'boolean'}},[oldkey,'active'])
    if kind=='removed':new=spec({'active':{'type':'boolean'}},['active'])
    source=f'def parse(payload):\n    return {{"value": payload["{oldkey}"], "active": payload["active"], "literal": "{oldkey}"}}\n'
    cases=[{'response':{newkey:f'customer-{i}','active':bool(i%2)},'expected':{'value':f'customer-{i}','active':bool(i%2),'literal':oldkey}} for i in range(5)]
    return {'old':old,'new':new,'source':source,'cases':cases,'kind':kind}
