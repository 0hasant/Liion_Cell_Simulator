import os, copy
from sexp import parse, Q, find
LIBDIR='/usr/share/kicad/symbols'
_cache={}
def libfile(lib):
    if lib not in _cache:
        _cache[lib]=parse(open(os.path.join(LIBDIR,lib+'.kicad_sym')).read())[0]
    return _cache[lib]
def get(libid):
    lib,name=libid.split(':')
    L=libfile(lib)
    for s in find(L,'symbol'):
        if s[1]==name:
            s=copy.deepcopy(s)
            ext=find(s,'extends')
            if ext:
                base=get(lib+':'+ext[0][1])
                # take base graphics/pins, override properties
                props={p[1]:p for p in find(s,'property')}
                newb=[]
                for e in base:
                    if isinstance(e,list) and e[0]=='property' and e[1] in props: newb.append(props.pop(e[1]))
                    elif isinstance(e,list) and e[0]=='symbol':
                        e=copy.deepcopy(e); e[1]=Q(e[1].replace(ext[0][1],name,1)); newb.append(e)
                    else: newb.append(e)
                for p in props.values(): newb.append(p)
                s=newb
            s[1]=Q(libid)
            return s
    raise KeyError(libid)
def pins(sym):
    """return list of dict(number,name,x,y,angle,unit,type)"""
    out=[]
    for sub in find(sym,'symbol'):
        parts=sub[1].rsplit('_',2)
        unit=int(parts[-2])
        for p in find(sub,'pin'):
            at=find(p,'at')[0]
            name=find(p,'name')[0][1]; num=find(p,'number')[0][1]
            hidden='hide' in p
            out.append(dict(number=str(num),name=str(name),x=float(at[1]),y=float(at[2]),angle=float(at[3]) if len(at)>3 else 0.0,unit=unit,type=p[1],hidden=hidden))
    return out
