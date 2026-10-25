const test=require('node:test'),assert=require('node:assert/strict');
const {versionCode,releaseInfo}=require('../assets/life-update-core.js');
const release=(version)=>({tag_name:`android-v${version}`,html_url:`https://github.com/V0van200/Life/releases/tag/android-v${version}`,assets:[{name:`Life-${version}.apk`,size:100,browser_download_url:`https://github.com/V0van200/Life/releases/download/android-v${version}/Life-${version}.apk`}],body:'Changes'});
test('version order and malformed versions',()=>{assert.equal(versionCode('0.7.0'),7000);assert.ok(versionCode('0.10.0')>versionCode('0.9.99'));for(const v of ['1.1000.0','1.0.1000','01.0.0','0.7.0-beta','-1.0.0','99999999.0.0'])assert.equal(versionCode(v),null)});
test('only newer stable matching APK releases',()=>{assert.equal(releaseInfo(release('0.7.0'),7000),null);assert.equal(releaseInfo({...release('0.8.0'),draft:true},7000),null);assert.equal(releaseInfo({...release('0.8.0'),prerelease:true},7000),null);assert.equal(releaseInfo(release('0.7.1'),7000).version,'0.7.1');});
test('reject foreign links and absent APKs',()=>{for(const r of [{...release('0.8.0'),html_url:'https://evil.example'}, {...release('0.8.0'),assets:[]}])assert.throws(()=>releaseInfo(r,7000));const r=release('0.8.0');r.assets[0].browser_download_url='https://evil.example/payload.apk';assert.throws(()=>releaseInfo(r,7000));});

const {manifestInfo}=require('../assets/life-update-core.js');
const manifest={appId:'ru.vovan20.life',version:'0.7.1',versionCode:7001,sha256:'a'.repeat(64),url:'https://raw.githubusercontent.com/V0van200/Life/android-releases/Life-0.7.1.apk'};
test('signed APK channel metadata validation',()=>{assert.equal(manifestInfo(manifest,7000).version,'0.7.1');assert.equal(manifestInfo(manifest,7001),null);for(const m of [{...manifest,url:'https://evil.example/a.apk'},{...manifest,versionCode:9000},{...manifest,appId:'other'},{...manifest,sha256:''}])assert.throws(()=>manifestInfo(m,7000));});
