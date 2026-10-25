const fs = require('node:fs');
const path = require('node:path');
const pkg = require('../package.json');
const [major, minor, patch] = pkg.version.split('.').map(Number);
if (![major, minor, patch].every(Number.isSafeInteger) || minor > 999 || patch > 999) throw Error('Invalid version');
const versionCode = major * 1000000 + minor * 1000 + patch;
fs.rmSync('www', {recursive:true, force:true});
fs.mkdirSync('www');
fs.cpSync('assets', 'www/assets', {recursive:true});
fs.copyFileSync('node_modules/@capacitor/core/dist/capacitor.js', 'www/assets/capacitor-runtime.js');
let html = fs.readFileSync('index.html','utf8');
// Capacitor needs explicit head/body elements to inject its native bridge.
html = html.replace('<html lang="ru">','<html lang="ru"><head>');
html = html.replace('<aside>', '</head><body><aside>');
html = html.replace('</html>', '<script src="assets/capacitor-runtime.js"></script><script src="assets/life-update-core.js"></script><script src="assets/life-android.js"></script></body></html>');
html = html.replace('width=device-width,initial-scale=1','width=device-width,initial-scale=1,viewport-fit=cover');
fs.writeFileSync('www/index.html', html);
let comfort = fs.readFileSync('www/assets/life-comfort.js','utf8');
comfort = comfort.replace("if(typeof navigator!=='undefined'&&navigator.serviceWorker)", "if(false)");
comfort = comfort.replace("if(typeof navigator!=='undefined'&&'serviceWorker' in navigator)", "if(false)");
comfort = comfort.replace('Записи находятся в этом браузере, без шифрования.', 'Записи находятся в хранилище приложения, без шифрования.');
comfort = comfort.replace('Android: меню Chrome → «Установить приложение» или «Добавить на главный экран». Первый запуск нужен с интернетом.', 'Life установлен на телефоне. Интернет нужен только для проверки и загрузки обновлений.');
comfort = comfort.replace('Офлайн-режим: проверяется…', 'Все экраны включены в APK и доступны без интернета.');
fs.writeFileSync('www/assets/life-comfort.js', comfort);
fs.writeFileSync('www/app-version.json', JSON.stringify({version:pkg.version,versionCode}));
if(fs.existsSync('android/app/build.gradle')){
 let gradle = fs.readFileSync('android/app/build.gradle','utf8');
 gradle = gradle.replace(/versionCode \d+/, `versionCode ${versionCode}`).replace(/versionName "[^"]+"/, `versionName "${pkg.version}"`);
 fs.writeFileSync('android/app/build.gradle',gradle);
}
console.log(`Built Life ${pkg.version} (${versionCode}), bundled offline assets`);
