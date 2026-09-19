import { useState, type MouseEvent } from "react";
import type { CalculationResult, ProfileInput } from "./types";
import { getProfile } from "./chartProfiles";

const fmt=(n:number,d=2)=>n.toFixed(d);
function junctionXs(profile:ProfileInput|undefined){
 if(!profile)return [];
 const points=profile.points;
 if(profile.mode==="xyb")return points.map(p=>p.x);
 const xs=[points[0].x];
 for(let i=1;i<points.length-1;i++){
  const a=points[i-1],b=points[i],c=points[i+1],r=b.value;
  const inX=b.x-a.x,inY=b.y-a.y,outX=c.x-b.x,outY=c.y-b.y,inL=Math.hypot(inX,inY),outL=Math.hypot(outX,outY);
  const angle=Math.acos(Math.max(-1,Math.min(1,(inX*outX+inY*outY)/(inL*outL))));
  const tangent=r>0?r*Math.tan(angle/2):0;
  xs.push(b.x-inX/inL*tangent,b.x+outX/outL*tangent);
 }
 xs.push(points.at(-1)!.x);return xs;
}
export default function Chart({result,planProfile,elevationProfile}:{result:CalculationResult;planProfile?:ProfileInput; elevationProfile?:ProfileInput}){
 const [tip,setTip]=useState<{i:number;x:number;y:number}|null>(null),d=result.distribution,w=920,h=150,l=88,r=25,x0=d[0].x,x1=d.at(-1)!.x,plot=w-l-r;
 const sx=(x:number)=>l+(x-x0)/(x1-x0)*plot;
 const rows:[keyof typeof d[number],string,string,ProfileInput|undefined][]=[["plan_y","平面 y","m",planProfile ?? getProfile("平面线形")],["elevation_y","立面 y","m",elevationProfile ?? getProfile("立面线形")],["stress","应力","MPa",undefined],["elongation_mm","伸长量","mm",undefined]];
 const hover=(e:MouseEvent<SVGRectElement>)=>{const b=e.currentTarget.ownerSVGElement!.getBoundingClientRect(),u=Math.max(0,Math.min(1,(e.clientX-b.left-b.width*l/w)/(b.width*plot/w))),x=x0+u*(x1-x0),i=d.reduce((best,p,index)=>Math.abs(p.x-x)<Math.abs(d[best].x-x)?index:best,0);setTip({i,x:e.clientX-b.left,y:e.clientY-b.top})};
 return <section className="panel chart"><h2>钢束综合分布</h2><div className="chart-wrap"><svg viewBox={`0 0 ${w} ${h*4+46}`} onMouseLeave={()=>setTip(null)}>{rows.map(([key,title,unit,profile],i)=>{const raw=d.map(p=>key==="elongation_mm"?Math.max(0,p[key] as number):p[key] as number),minimum=i===3?0:Math.min(...raw),maximum=Math.max(...raw),lo=maximum-minimum<.001?maximum-.001:minimum,hi=maximum,top=i*h+20,sy=(v:number)=>top+h-34-(v-lo)/(hi-lo)*(h-58),value=(p:typeof d[number])=>key==="elongation_mm"?Math.max(0,p[key] as number):p[key] as number,path=d.map((p,j)=>`${j?"L":"M"}${sx(p.x)},${sy(value(p))}`).join(" "),nearest=(x:number)=>d.reduce((best,p,index)=>Math.abs(p.x-x)<Math.abs(d[best].x-x)?index:best,0);return <g key={title}><rect x={l} y={top} width={plot} height={h-34} className="frame"/>{[.25,.5,.75].map(v=><line key={`h${v}`} x1={l} x2={w-r} y1={top+(h-34)*v} y2={top+(h-34)*v} className="gridline"/>)}{[.2,.4,.6,.8].map(v=><line key={`v${v}`} x1={l+plot*v} x2={l+plot*v} y1={top} y2={top+h-34} className="gridline"/>)}<text x="18" y={top+(h-34)/2-5} className="y-title">{title}</text><text x="18" y={top+(h-34)/2+10} className="y-title unit">({unit})</text><text x={l-8} y={top+11} textAnchor="end" className="tick">{fmt(hi,key==="stress"?0:2)}</text><text x={l-8} y={top+h-36} textAnchor="end" className="tick">{fmt(lo,key==="stress"?0:2)}</text><path d={path} className={`line line${i}`}/>{profile&&junctionXs(profile).map((x,j)=>{const p=d[nearest(x)];return <circle key={j} cx={sx(x)} cy={sy(value(p))} r="3" className={`keypoint keypoint${i}`}/>})}{result.balance_x!==null&&<><line x1={sx(result.balance_x)} x2={sx(result.balance_x)} y1={top} y2={top+h-34} className="balance"/>{i===0&&<text x={sx(result.balance_x)+4} y={top+13} className="red">不动点</text>}</>}<rect x={l} y={top} width={plot} height={h-34} className="hover-zone" onMouseMove={hover}/></g>})}{[0,.2,.4,.6,.8,1].map(v=><text key={v} x={l+plot*v} y={h*4+24} textAnchor={v===0?"start":v===1?"end":"middle"} className="tick">{fmt(x0+(x1-x0)*v)}</text>)}<text x={w/2} y={h*4+40} textAnchor="middle">x (m)</text></svg>{tip&&<div className="tooltip" style={{left:`${Math.min(tip.x+14,700)}px`,top:`${Math.max(tip.y-52,24)}px`}}>x = {fmt(d[tip.i].x)} m<br/>平面 y = {fmt(d[tip.i].plan_y)} m<br/>立面 y = {fmt(d[tip.i].elevation_y)} m<br/>应力 = {fmt(d[tip.i].stress,1)} MPa<br/>伸长量 = {fmt(Math.max(0,d[tip.i].elongation_mm))} mm</div>}</div></section>
}
