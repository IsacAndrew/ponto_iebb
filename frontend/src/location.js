// Aceitar a primeira leitura precisa; aguardar melhora das demais.
export function locate(){
 return new Promise((resolve,reject)=>{
  if(!navigator.geolocation){reject(new Error('Este navegador não oferece localização.'));return;}
  let best=null,watch=null,finished=false;
  const finish=(error)=>{if(finished)return;finished=true;clearTimeout(timer);if(watch!==null)navigator.geolocation.clearWatch(watch);if(best)resolve(best);else reject(error||new Error('Não foi possível obter sua localização. Confira a localização do sistema e tente novamente.'));};
  const timer=setTimeout(()=>finish(),8000);
  watch=navigator.geolocation.watchPosition(position=>{
   if(!best||position.coords.accuracy<best.coords.accuracy)best=position;
   if(position.coords.accuracy<=100)finish();
  },error=>finish(new Error(error.code===1?'Permita a localização nas configurações deste site.':'Não foi possível obter a localização deste aparelho. Confira a localização do sistema e tente novamente.')),{enableHighAccuracy:true,timeout:8000,maximumAge:15000});
 });
}
