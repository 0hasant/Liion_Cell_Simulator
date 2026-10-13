import re
TOK = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')
def parse(s):
    stack=[[]]; pos=0
    while True:
        m=TOK.match(s,pos)
        if not m or m.end()==pos: break
        pos=m.end()
        if m.group(1): stack.append([])
        elif m.group(2):
            t=stack.pop(); stack[-1].append(t)
        elif m.group(3): stack[-1].append(Q(m.group(3)[1:-1].replace('\\"','"').replace('\\\\','\\')))
        else: stack[-1].append(m.group(4))
    return stack[0]
class Q(str): pass
def dump(x, ind=0):
    if isinstance(x,list):
        if not x: return '()'
        simple = all(not isinstance(e,list) for e in x)
        if simple: return '('+' '.join(dump(e) for e in x)+')'
        out='('+dump(x[0]) if not isinstance(x[0],list) else '('
        for e in x[1:]:
            if isinstance(e,list): out+='\n'+'  '*(ind+1)+dump(e,ind+1)
            else: out+=' '+dump(e)
        return out+')'
    if isinstance(x,Q): return '"'+x.replace('\\','\\\\').replace('"','\\"')+'"'
    return str(x)
def find(x, key):
    return [e for e in x if isinstance(e,list) and e and e[0]==key]
