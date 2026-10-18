import pathlib,json,gzip,hashlib,base64
from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
p=pathlib.Path(__file__).resolve().parents[1]/'Tests/Fixtures';p.mkdir(exist_ok=True);(p/'objects').mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest();objects={};locales=[]
for code,values in [('es',{'data/System.KEL':b'spanish resource','fonts/Only-ES.ttf':b'spanish font'}),('fr',{'data/System.KEL':b'french resource','fonts/Only-FR.ttf':b'french font'})]:
 files={}
 for name,b in values.items():
  iv=bytes(range(16)) if name.endswith('.KEL') else b''
  if iv:
   c=Cipher(algorithms.AES(b'6bdb2e585882fbd48826ef9cffd4c511'),modes.CTR(iv)).encryptor();raw=iv+c.update(b)+c.finalize()
  else:raw=b
  obj=sha(b);z=gzip.compress(b,mtime=0);(p/'objects'/obj).write_bytes(z);objects[obj]={'sha256':sha(z),'bytes':len(z),'unpackedBytes':len(b)};files[name]={'object':obj,'sha256':sha(raw),'bytes':len(raw),'iv':base64.b64encode(iv).decode()}
 locales.append({'code':code,'name':code,'files':files,'reviewStatus':'test-only'})
j={'schemaVersion':1,'game':'OMORI','steamAppID':'1150690','sourceBuild':'8879120','version':'test','runtimeCode':'en','originals':{'data/System.KEL':sha(b'official system')},'objects':objects,'locales':locales}
b=json.dumps(j,separators=(',',':')).encode();(p/'catalog.json').write_bytes(b);(p/'expected.sha256').write_text(sha(b))
