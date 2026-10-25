/* Strictly validate metadata before presenting an external download. */
(function(root){
 function versionCode(version){
  const m=/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.exec(version||'');
  if(!m)return null;
  const [a,b,c]=m.slice(1).map(Number),n=a*1000000+b*1000+c;
  return b<=999&&c<=999&&Number.isSafeInteger(n)&&n<=2100000000?n:null;
 }
 function releaseInfo(release,current){
  if(!release||release.draft||release.prerelease)return null;
  const m=/^android-v(.+)$/.exec(release.tag_name||'');
  const code=m?versionCode(m[1]):null;
  if(code===null||code<=current)return null;
  const url=`https://github.com/V0van200/Life/releases/tag/${release.tag_name}`;
  const asset=`Life-${m[1]}.apk`;
  if(release.html_url!==url||!Array.isArray(release.assets)||!release.assets.some(a=>a.name===asset&&a.size>0&&a.browser_download_url===`https://github.com/V0van200/Life/releases/download/${release.tag_name}/${asset}`))throw Error('В выпуске нет корректного установочного APK');
  return {version:m[1],code,url,notes:String(release.body||'').slice(0,4000)};
 }
 function manifestInfo(m,current){
  const code=versionCode(m?.version);
  if(!m||m.appId!=='ru.vovan20.life'||code===null||code!==m.versionCode||!/^([a-f0-9]{64})$/.test(m.sha256||''))throw Error('Некорректное описание обновления');
  const raw=`https://raw.githubusercontent.com/V0van200/Life/android-releases/Life-${m.version}.apk`;
  const release=`https://github.com/V0van200/Life/releases/download/android-v${m.version}/Life-${m.version}.apk`;
  if(m.url!==raw&&m.url!==release)throw Error('Недопустимый адрес APK');
  return code>current?{version:m.version,code,url:m.url,notes:String(m.notes||'').slice(0,4000)}:null;
 }
 const api={versionCode,releaseInfo,manifestInfo};root.LifeUpdates=api;
 if(typeof module!=='undefined')module.exports=api;
})(globalThis);
