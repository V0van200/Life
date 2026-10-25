// Run in GitHub Actions AFTER the signed release asset has been published.
const fs=require('node:fs'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process');
const {version}=require('../package.json'),{versionCode}=require('../assets/life-update-core.js');
const manifest={appId:'ru.vovan20.life',version,versionCode:versionCode(version),sha256:crypto.createHash('sha256').update(fs.readFileSync(`release/Life-${version}.apk`)).digest('hex'),url:`https://github.com/V0van200/Life/releases/download/android-v${version}/Life-${version}.apk`,notes:`Обновление Life ${version}. Перед установкой рекомендуется сохранить резервную копию.`};
const endpoint='repos/V0van200/Life/contents/latest.json';
const current=JSON.parse(execFileSync('gh',['api',endpoint+'?ref=android-releases'],{encoding:'utf8'}));
execFileSync('gh',['api','--method','PUT',endpoint,'--input','-'],{input:JSON.stringify({message:`Publish Android ${version}`,branch:'android-releases',sha:current.sha,content:Buffer.from(JSON.stringify(manifest,null,2)).toString('base64')}),stdio:['pipe','ignore','inherit']});
console.log('Published update metadata',version);
