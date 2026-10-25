"""Sign only with an explicitly supplied, permanent release key. Never generate one here."""
import hashlib, json, os, pathlib, subprocess
root = pathlib.Path(__file__).resolve().parent.parent
version = json.loads((root / 'package.json').read_text())['version']
tools = pathlib.Path(os.environ['LIFE_BUILD_TOOLS'])
key = pathlib.Path(os.environ['LIFE_KEYSTORE'])
assert key.is_file(), 'Permanent signing key not found'
for name in ['LIFE_STORE_PASSWORD','LIFE_KEY_PASSWORD','LIFE_KEY_ALIAS']:
    assert os.environ.get(name), f'{name} is required'
out = root / 'release'; out.mkdir(exist_ok=True)
aligned = out / 'aligned-unsigned.apk'
apk = out / f'Life-{version}.apk'
subprocess.run([str(tools/'zipalign'),'-f','-p','4',str(root/'android/app/build/outputs/apk/release/app-release-unsigned.apk'),str(aligned)],check=True)
subprocess.run([str(tools/'apksigner'),'sign','--ks',str(key),'--ks-key-alias',os.environ['LIFE_KEY_ALIAS'],'--ks-pass','env:LIFE_STORE_PASSWORD','--key-pass','env:LIFE_KEY_PASSWORD','--out',str(apk),str(aligned)],check=True)
subprocess.run([str(tools/'apksigner'),'verify','--verbose','--print-certs',str(apk)],check=True)
(apk.with_suffix('.apk.sha256')).write_text(hashlib.sha256(apk.read_bytes()).hexdigest()+'  '+apk.name+'\n')
aligned.unlink()
print(apk)
