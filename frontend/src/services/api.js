const BASE=import.meta.env.VITE_API_URL||'http://localhost:8000/api';
export async function api(path,options={}){const response=await fetch(BASE+path,options);if(!response.ok){const data=await response.json().catch(()=>({}));throw new Error(data.detail||`Request failed (${response.status})`)}return response.json()}
export const post=(path,data)=>api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
