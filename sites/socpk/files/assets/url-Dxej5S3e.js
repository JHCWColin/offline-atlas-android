function e(r){const t=r.trim();if(!t)return!0;if(t.startsWith("/"))return!t.startsWith("//");try{return new URL(t).protocol==="https:"}catch{return!1}}export{e as i};
