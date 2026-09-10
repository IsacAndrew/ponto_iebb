let cached=null,pending=null;
function recent(){return cached&&Date.now()-cached.timestamp<30000&&cached.coords.accuracy<=500?cached:null}
export function locate(){
 const ready=recent();if(ready)return Promise.resolve(ready);if(pending)return pending;
 if(!navigator.geolocation)return Promise.reject(new Error('Este navegador não oferece localização.'));
 pending=new Promise((resolve,reject)=>{
  let best=null,watch=null,finished=false;
  const finish=error=>{if(finished)return;finished=true;clearTimeout(timer);if(watch!==null)navigator.geolocation.clearWatch(watch);if(best){cached=best;resolve(best)}else reject(error||new Error('Não foi possível obter sua localização. Confira a permissão deste site.'))};
  const timer=setTimeout(()=>finish(),5000);
  watch=navigator.geolocation.watchPosition(position=>{
   if(!best||position.coords.accuracy<best.coords.accuracy)best=position;
   if(position.coords.accuracy<=500)finish();
  },error=>finish(new Error(error.code===1?'Permita a localização nas configurações deste site.':'Não foi possível obter a localização deste aparelho. Confira a localização do sistema e tente novamente.')),{enableHighAccuracy:true,timeout:5000,maximumAge:30000});
 }).finally(()=>{pending=null});
 return pending;
}
export function warmLocation(){locate().catch(()=>{})}
