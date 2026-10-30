const groups={Documentos:['pdf','txt','doc','docx','odt','rtf','ppt','pptx','epub'],Imagens:['png','jpg','jpeg','gif','webp','bmp','svg','heic'],Videos:['mp4','mkv','avi','mov','webm','wmv'],Musicas:['mp3','wav','flac','ogg','m4a','aac'],Planilhas:['xls','xlsx','csv','ods'],Compactados:['zip','rar','7z','tar','gz','bz2','xz']};
export function category(name){const ext=name.includes('.')?name.split('.').pop().toLowerCase():'';return Object.keys(groups).find(k=>groups[k].includes(ext))||'Outros';}
const key=s=>s.normalize('NFC').toLowerCase();
export function plan(files,existing=[]){
 const reserved=new Set(existing.map(x=>key(x.trim())));return files.map(file=>{
 const name=String(file.name),size=Number(file.size)||0;
 if(!name||name.length>255||/[\\/\x00-\x1f]/.test(name))return {name,size,status:'Ignorado',reason:'Nome inválido'};
 const ext=name.split('.').pop().toLowerCase();
 if(name.startsWith('.')||['part','crdownload','tmp','download'].includes(ext)||name==='organizador-operacoes.jsonl')return {name,size,status:'Ignorado',reason:'Oculto, incompleto ou log'};
 const folder=category(name);let target=name,index=0;const dot=name.lastIndexOf('.'),stem=dot>0?name.slice(0,dot):name,suffix=dot>0?name.slice(dot):'';
 while(reserved.has(key(folder+'/'+target))){index++;target=stem+' ('+index+')'+suffix;}
 reserved.add(key(folder+'/'+target));return {name,size,category:folder,destination:folder+'/'+target,status:index?'Renomeado':'Simulado',conflict:index>0};
 });
}
export const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
