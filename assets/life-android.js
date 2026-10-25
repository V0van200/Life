/* Native-only shell; added to the APK, never loaded by the website. */
(function(){
 const cap=window.Capacitor;if(!cap?.isNativePlatform())return;
 const App=cap.registerPlugin('App'),Http=cap.registerPlugin('CapacitorHttp');
 const Files=cap.registerPlugin('Filesystem'),Share=cap.registerPlugin('Share');
 let info=null,latest=null,busy=false,message='Проверка доступна при подключении к интернету.';
 const previousRender=render;
 function panel(){
  if(page!=='more'||goalView||insightsView)return;
  const old=document.getElementById('android-updates');if(old)old.remove();
  document.getElementById('view').insertAdjacentHTML('afterbegin',`<div class="card" id="android-updates"><span class="tag">LIFE ДЛЯ ANDROID</span><h2>Обновления</h2><p>Версия ${esc(info?.version||'…')} · данные остаются на телефоне</p><p role="status">${esc(message)}</p><div class="ui-footer-actions"><button id="check-life-update" ${busy?'disabled':''}>${busy?'Проверяем…':'Проверить обновления'}</button>${latest?`<a href="${latest.url}" target="_blank" rel="noopener noreferrer" style="display:inline-block;padding:12px;color:#c6baff">Скачать Life ${esc(latest.version)}</a>`:''}</div>${latest?`<p style="white-space:pre-wrap">${esc(latest.notes)}</p>`:''}<p>Установи новый APK поверх текущего приложения. Не удаляй Life перед обновлением. Android попросит подтвердить установку.</p><p>Перед обновлением сохрани резервную копию. Данные пока без шифрования.</p></div>`);
  document.getElementById('check-life-update').onclick=()=>check();
 }
 render=function(){previousRender();panel();const badge=document.querySelector('.ui-version');if(badge)badge.textContent='LIFE ANDROID '+(info?.version||'');};
 async function check(){
  if(busy)return;busy=true;message='Проверяем выпуски Life…';panel();
  try{
   info=info||await App.getInfo();
   const response=await Http.get({url:'https://raw.githubusercontent.com/V0van200/Life/android-releases/latest.json',headers:{Accept:'application/json','Cache-Control':'no-cache'},connectTimeout:10000,readTimeout:15000});
   if(response.status===403||response.status===429)throw Error('Лимит проверок. Попробуй позже.');
   if(response.status!==200)throw Error('Сервис обновлений сейчас недоступен.');
   const manifest=typeof response.data==='string'?JSON.parse(response.data):response.data;
   latest=LifeUpdates.manifestInfo(manifest,Number(info.build));
   message=latest?`Доступна версия ${latest.version}.`:'Новых опубликованных Android-версий пока нет.';
  }catch(e){latest=null;message=e.message||'Нет соединения. Life продолжает работать офлайн.';}
  finally{busy=false;panel();}
 }
 backup=async function(){
  try{
   const result=await Files.writeFile({path:'life-backup.json',data:JSON.stringify({version:1,records:data},null,2),directory:'CACHE',encoding:'utf8'});
   await Share.share({title:'Резервная копия Life',url:result.uri,dialogTitle:'Сохрани копию в личное хранилище'});
  }catch(e){toast('Не удалось сохранить копию: '+(e.message||'операция отменена'));}
 };
 App.addListener('backButton',()=>{
  const dialog=document.querySelector('dialog[open]');if(dialog){dialog.close();return;}
  if(page!=='home'){go('home');return;}App.minimizeApp();
 });
 App.getInfo().then(value=>{info=value;render();}).catch(()=>{});
 render();
})();
