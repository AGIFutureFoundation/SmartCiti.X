// usage: node patch_cycle.mjs <n> [videoPath]  — refresh a cycle's gates/checks from loop/state and attach its video
import {readFileSync,writeFileSync} from 'node:fs';import {execFileSync} from 'node:child_process';
const [n,video]=process.argv.slice(2);const L='loop/registry/cycles.json';
const led=JSON.parse(readFileSync(L));const c=led.cycles.find(x=>x.n===+n);
const ev=JSON.parse(readFileSync('loop/state/evals_latest.json'));
c.gates=ev.gates.map(g=>({id:g.id,name:g.name,status:g.status,detail:g.detail,ms:g.ms??0}));
const m=(ev.gates.find(g=>g.id==='EV-01').detail||'').match(/(\d+) checks/);if(m)c.checks_total=+m[1];
if(video){const d=+execFileSync('ffprobe',['-v','error','-show_entries','format=duration','-of','csv=p=0',video]).toString();c.video={path:video,duration_s:+d.toFixed(3)};}
c.agents=c.agents.map(a=>({...a,result:a.result.replace('review_c0.mp4','review_c1.mp4')}));
writeFileSync(L,JSON.stringify(led,null,2)+'\n');console.log('cycle',n,'gates',c.gates.map(g=>g.id+':'+g.status).join(' '),'checks',c.checks_total,'video',c.video&&c.video.duration_s);
