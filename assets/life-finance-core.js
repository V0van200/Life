/* Money in integer kopecks. Wallet payouts are transfers, never a second income. */
(function(root){
 const types=['accrual','adjustment','payout'];
 const statuses=['pending','available'];
 const financial=r=>['income','expense','work','opening'].includes(r.kind);
 function validate(r){
  if(!r||typeof r.id!=='string'||!/^[a-zA-Z0-9-]+$/.test(r.id)||typeof r.title!=='string'||!r.title.trim()||r.title.length>120)throw Error('Проверь название операции');
  const checkDate=s=>{if(!/^\d{4}-\d{2}-\d{2}$/.test(s||''))throw Error('Укажи дату');const [y,m,d]=s.split('-').map(Number),date=new Date(y,m-1,d,12);if(date.getFullYear()!==y||date.getMonth()!==m-1||date.getDate()!==d)throw Error('Некорректная дата');};
  checkDate(r.date);
  if(!Number.isSafeInteger(r.amount)||Math.abs(r.amount)>100000000000||r.amount===0)throw Error('Введи ненулевую сумму до 1 млрд ₽');
  if(r.kind==='work'){
   if(!types.includes(r.entryType))throw Error('Выбери тип рабочей операции');
   if(r.entryType==='payout'){
    if(r.amount<0||!['pending','completed'].includes(r.status))throw Error('Для выплаты нужна положительная сумма и статус');
   }else{checkDate(r.workDate);if(!statuses.includes(r.status))throw Error('Выбери статус начисления');}
  }else{
   if(!['bank','wallet'].includes(r.account||'bank'))throw Error('Выбери счёт');
   if(['income','expense'].includes(r.kind)&&r.amount<0)throw Error('Для расхода или дохода введи положительную сумму');
   if(r.kind==='opening'&&r.account==='wallet'&&!statuses.includes(r.status))throw Error('Выбери статус остатка');
  }
  if(r.note!==undefined&&(typeof r.note!=='string'||r.note.length>5000))throw Error('Заметка должна быть до 5000 символов');
  return r;
 }
 function totals(records){
  let result={bank:0,wallet:0,pending:0,income:0,expense:0,accrual:0,adjustment:0,payout:0,payoutPending:0,opening:0};
  for(const r of records.filter(r=>!r.archived)){
   if(!financial(r))continue;
   if(r.kind==='work'){
    if(r.entryType==='payout'){
     if(r.status==='completed'){result.wallet-=r.amount;result.bank+=r.amount;result.payout+=r.amount;}else result.payoutPending+=r.amount;
    }else{
     result[r.status==='pending'?'pending':'wallet']+=r.amount;
     result[r.entryType==='accrual'?'accrual':'adjustment']+=r.amount;
    }
   }else if(r.kind==='opening'){
    result.opening+=r.amount;
    result[r.account==='wallet'?(r.status==='pending'?'pending':'wallet'):'bank']+=r.amount;
   }else{
    const delta=r.kind==='income'?r.amount:-r.amount;
    result[r.account==='wallet'?'wallet':'bank']+=delta;
    result[r.kind==='income'?'income':'expense']+=r.amount;
   }
  }
  result.workNet=result.accrual+result.adjustment;
  result.totalIncome=result.income+result.workNet;
  result.available=result.bank+result.wallet;
  result.total=result.available+result.pending;
  return result;
 }
 function dayTotals(records,date){
  let result={accrual:0,adjustment:0,net:0,pending:0};
  for(const r of records.filter(r=>!r.archived&&r.kind==='work'&&r.entryType!=='payout'&&r.workDate===date)){
   result[r.entryType]+=r.amount;if(r.status==='pending')result.pending+=r.amount;
  }
  result.net=result.accrual+result.adjustment;return result;
 }
 const api={financial,validate,totals,dayTotals};root.LifeFinance=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
