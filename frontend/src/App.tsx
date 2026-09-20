import { useEffect, useState, type ChangeEvent, type ClipboardEvent, type MouseEvent } from "react";
import type { CalculationResult, DxfImportResponse, ProfileInput } from "./types";
import Chart from "./Chart";
import { rememberProfile } from "./chartProfiles";
import { apiUrl } from "./api";

const elevation: ProfileInput={mode:"xyr",points:[[0,0,0],[5.191,-1.294,10],[27.647,-1.294,10],[32.273,-.141,10],[42.729,-.141,10],[47.355,-1.294,10],[69.811,-1.294,10],[75,0,0]].map(([x,y,value])=>({x,y,value}))};
const plan: ProfileInput={mode:"xyr",points:[[0,0,0],[25,3.4613,100],[75,0,0]].map(([x,y,value])=>({x,y,value}))};
const fmt=(n:number,d=3)=>Number.isFinite(n)?n.toFixed(d):"—";
const fields=["x","y","value"] as const;

function LegacyEditor({title,value,onChange}:{title:string;value:ProfileInput;onChange:(x:ProfileInput)=>void}){
 rememberProfile(title,value);
 const [active,setActive]=useState({row:0,column:0}),[anchor,setAnchor]=useState({row:0,column:0});
 const selected=(row:number,column:number)=>row>=Math.min(anchor.row,active.row)&&row<=Math.max(anchor.row,active.row)&&column>=Math.min(anchor.column,active.column)&&column<=Math.max(anchor.column,active.column);
 const set=(i:number,k:typeof fields[number],v:string)=>onChange({...value,points:value.points.map((p,j)=>j===i?{...p,[k]:Number(v)}:p)});
 const paste=(event:ClipboardEvent<HTMLTableElement>)=>{const rows=event.clipboardData.getData("text").replace(/\r/g,"").split("\n").filter(Boolean).map(row=>row.split(/\t|,/).map(cell=>cell.trim()));if(!rows.length)return;event.preventDefault();const focus=document.activeElement as HTMLInputElement|null,startRow=Number(focus?.dataset.row??active.row),startColumn=Number(focus?.dataset.column??active.column),points=value.points.map(p=>({...p}));while(points.length<startRow+rows.length)points.push({x:0,y:0,value:0});rows.forEach((row,ri)=>row.forEach((cell,ci)=>{const col=startColumn+ci,n=Number(cell);if(col<3&&cell!==""&&Number.isFinite(n))points[startRow+ri][fields[col]]=n}));onChange({...value,points})};
 const xs=value.points.map(p=>p.x),ys=value.points.map(p=>p.y),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys),px=(x:number)=>8+(x-minX)/(maxX-minX||1)*164,py=(y:number)=>48-(y-minY)/(maxY-minY||1)*40;
 return <section className="panel"><div className="head"><div><h2>{title}</h2><small>{value.mode==="xyr"?"角点 + 倒角半径":"CAD 节点 + bulge；b 属于当前点到下一点"}</small></div><select value={value.mode} onChange={e=>onChange({...value,mode:e.target.value as "xyr"|"xyb"})}><option value="xyr">x / y / r</option><option value="xyb">x / y / b</option></select></div><div className="profile-preview"><span>线形预览</span><svg viewBox="0 0 180 58"><polyline points={value.points.map(p=>`${px(p.x)},${py(p.y)}`).join(" ")}/>{value.points.map((p,i)=><circle key={i} cx={px(p.x)} cy={py(p.y)} r="2.5"/>)}</svg></div><table className="sheet" onPaste={paste}><thead><tr><th>#</th><th>x (m)</th><th>y (m)</th><th>{value.mode==="xyr"?"r (m)":"b"}</th><th/></tr></thead><tbody>{value.points.map((p,i)=><tr key={i}><td>{i+1}</td>{fields.map((key,column)=><td key={key}><input className={`input-cell ${selected(i,column)?"selected-cell":""}`} type="text" inputMode="decimal" data-row={i} data-column={column} value={p[key]} onMouseDown={event=>{if(!event.shiftKey)setAnchor({row:i,column});setActive({row:i,column})}} onMouseEnter={event=>event.buttons===1&&setActive({row:i,column})} onFocus={()=>setActive({row:i,column})} onChange={e=>set(i,key,e.target.value)}/></td>)}<td><button className="delete" aria-label="删除该节点" onClick={()=>value.points.length>2&&onChange({...value,points:value.points.filter((_,j)=>j!==i)})}>×</button></td></tr>)}</tbody></table><small>单击单元格后，可从 Excel 粘贴任意行、列；仅在行数不足时自动增加节点。拖动或 Shift 点击可框选范围。</small><button onClick={()=>onChange({...value,points:[...value.points,{...value.points.at(-1)!,x:value.points.at(-1)!.x+5,value:0}]})}>+ 添加节点</button></section>
}

function ProfileCell({value,row,column,onValue}:{value:number;row:number;column:number;onValue:(value:number)=>void}){
 const [text,setText]=useState(()=>value.toFixed(3)),[editing,setEditing]=useState(false);
 useEffect(()=>{if(!editing)setText(value.toFixed(3))},[value,editing]);
 return <input className="input-cell" type="text" inputMode="decimal" data-row={row} data-column={column} value={text} onFocus={()=>{setEditing(true);setText(String(value))}} onChange={event=>{const next=event.target.value,numberValue=Number(next);setText(next);if(next!==""&&Number.isFinite(numberValue))onValue(numberValue)}} onBlur={()=>{setEditing(false);if(text===""||!Number.isFinite(Number(text)))onValue(0)}}/>;
}

function Editor({title,value,onChange}:{title:string;value:ProfileInput;onChange:(x:ProfileInput)=>void}){
 rememberProfile(title,value);
 const set=(index:number,key:typeof fields[number],raw:string)=>{
  const numberValue=Number(raw);
  onChange({...value,points:value.points.map((point,i)=>i===index?{...point,[key]:Number.isFinite(numberValue)?numberValue:0}:point)});
 };
 const paste=(event:ClipboardEvent<HTMLTableElement>)=>{
  const rows=event.clipboardData.getData("text").replace(/\r/g,"").split("\n").filter(Boolean).map(row=>row.split(/\t|,/).map(cell=>cell.trim()));
  if(!rows.length)return;
  event.preventDefault();
  const focus=document.activeElement as HTMLInputElement|null;
  const startRow=Number(focus?.dataset.row??0),startColumn=Number(focus?.dataset.column??0);
  const points=value.points.map(point=>({...point}));
  while(points.length<startRow+rows.length)points.push({x:0,y:0,value:0});
  rows.forEach((row,rowIndex)=>row.forEach((cell,columnIndex)=>{
   const column=startColumn+columnIndex,numberValue=Number(cell);
   if(column<fields.length&&cell!==""&&Number.isFinite(numberValue))points[startRow+rowIndex][fields[column]]=numberValue;
  }));
  onChange({...value,points});
 };
 const xs=value.points.map(point=>point.x),ys=value.points.map(point=>point.y);
 const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
 const px=(x:number)=>8+(x-minX)/(maxX-minX||1)*164,py=(y:number)=>48-(y-minY)/(maxY-minY||1)*40;
 return <section className="panel"><div className="head"><div><h2>{title}</h2><small>{value.mode==="xyr"?"角点 + 倒角半径":"CAD 节点 + bulge；b 属于当前点到下一点"}</small></div><select value={value.mode} onChange={event=>onChange({...value,mode:event.target.value as "xyr"|"xyb"})}><option value="xyr">x / y / r</option><option value="xyb">x / y / b</option></select></div><div className="profile-preview"><span>线形预览</span><svg viewBox="0 0 180 58"><polyline points={value.points.map(point=>`${px(point.x)},${py(point.y)}`).join(" ")}/>{value.points.map((point,index)=><circle key={index} cx={px(point.x)} cy={py(point.y)} r="2.5"/>)}</svg></div><table className="sheet" onPaste={paste}><thead><tr><th>#</th><th>x (m)</th><th>y (m)</th><th>{value.mode==="xyr"?"r (m)":"b"}</th><th/></tr></thead><tbody>{value.points.map((point,index)=><tr key={index}><td>{index+1}</td>{fields.map((key,column)=><td key={key}><ProfileCell value={point[key]} row={index} column={column} onValue={numberValue=>set(index,key,String(numberValue))}/></td>)}<td><button className="delete" aria-label="删除该节点" onClick={()=>value.points.length>1&&onChange({...value,points:value.points.filter((_,i)=>i!==index)})}>×</button></td></tr>)}</tbody></table><div className="table-actions"><button className="clear" onClick={()=>onChange({...value,points:[{x:0,y:0,value:0}]})}>一键清空</button><button onClick={()=>onChange({...value,points:[...value.points,{x:0,y:0,value:0}]})}>+ 添加节点</button></div></section>;
}

function DxfImportControl({onImported}:{onImported:(elevation:ProfileInput,plan:ProfileInput)=>void}){
 const [unit,setUnit]=useState<"m"|"mm">("m"),[message,setMessage]=useState(""),[busy,setBusy]=useState(false);
 const upload=async(event:ChangeEvent<HTMLInputElement>)=>{
  const file=event.target.files?.[0];
  event.target.value="";
  if(!file)return;
  setBusy(true);setMessage("");
  try{
   const form=new FormData();form.append("file",file);
   const response=await fetch(apiUrl(`/api/import/dxf?unit=${unit}`),{method:"POST",body:form});
   const data=await response.json();
   if(!response.ok)throw new Error(typeof data.detail==="string"?data.detail:"DXF 导入失败");
   const result=data as DxfImportResponse;
   onImported(result.elevation,result.plan);
   setMessage(`导入完成：立面 ${result.elevation.points.length} 个节点，平面 ${result.plan.points.length} 个节点。`);
  }catch(error){setMessage(error instanceof Error?error.message:"DXF 导入失败")}finally{setBusy(false)}
 };
 return <div className="dxf-import"><div><strong>DXF 导入</strong><small>仅读取“立面”和“平面”图层；每层须且仅须一条开放二维多段线。</small></div><label>图纸单位<select value={unit} onChange={event=>setUnit(event.target.value as "m"|"mm")}><option value="m">m</option><option value="mm">mm</option></select></label><label className="primary import-file">{busy?"导入中…":"导入 DXF"}<input type="file" accept=".dxf" disabled={busy} onChange={upload}/></label>{message&&<small className={message.startsWith("导入完成")?"import-success":"import-error"}>{message}</small>}</div>;
}

function LegacyChart({result}:{result:CalculationResult}){
 const [tip,setTip]=useState<{x:number;y:number;i:number}|null>(null),d=result.distribution,w=920,h=150,l=88,r=25,x0=d[0].x,x1=d.at(-1)!.x,sx=(x:number)=>l+(x-x0)/(x1-x0)*(w-l-r);
 const rows:[keyof typeof d[number],string,string][]=[["plan_y","平面 y","m"],["elevation_y","立面 y","m"],["stress","应力","MPa"],["elongation_mm","累计伸长量","mm"]];
 const hover=(e:MouseEvent<SVGRectElement>)=>{const box=e.currentTarget.ownerSVGElement!.getBoundingClientRect(),plotLeft=box.width*l/w,plotWidth=box.width*(w-l-r)/w,x=x0+Math.max(0,Math.min(1,(e.clientX-box.left-plotLeft)/plotWidth))*(x1-x0),i=d.reduce((best,p,index)=>Math.abs(p.x-x)<Math.abs(d[best].x-x)?index:best,0);setTip({x:e.clientX-box.left,y:e.clientY-box.top,i})};
 return <section className="panel chart"><h2>钢束综合分布</h2><div className="chart-wrap"><svg viewBox={`0 0 ${w} ${h*4+46}`} onMouseLeave={()=>setTip(null)}>{rows.map(([key,title,unit],i)=>{const vals=d.map(p=>p[key] as number),mn=Math.min(...vals),mx=Math.max(...vals),pad=Math.max((mx-mn)*.12,.001),lo=mn-pad,hi=mx+pad,top=i*h+20,sy=(v:number)=>top+h-34-(v-lo)/(hi-lo)*(h-58),path=d.map((p,j)=>`${j?"L":"M"}${sx(p.x)},${sy(p[key] as number)}`).join(" ");return <g key={title}><rect x={l} y={top} width={w-l-r} height={h-34} className="frame"/>{[.25,.5,.75].map(v=><line key={v} x1={l} x2={w-r} y1={top+(h-34)*v} y2={top+(h-34)*v} className="gridline"/>)}<text x="18" y={top+(h-34)/2} className="y-title">{title} ({unit})</text><text x={l-8} y={top+11} textAnchor="end" className="tick">{fmt(hi,key==="stress"?0:2)}</text><text x={l-8} y={top+h-36} textAnchor="end" className="tick">{fmt(lo,key==="stress"?0:2)}</text><line x1={l} x2={w-r} y1={sy(0)} y2={sy(0)} className="zero"/><path d={path} className={`line line${i}`}/>{result.balance_x!==null&&<><line x1={sx(result.balance_x)} x2={sx(result.balance_x)} y1={top} y2={top+h-34} className="balance"/>{i===0&&<text x={sx(result.balance_x)+4} y={top+13} className="red">不动点</text>}</>}<rect x={l} y={top} width={w-l-r} height={h-34} className="hover-zone" onMouseMove={hover}/></g>})}<text x={l} y={h*4+24} className="tick">{fmt(x0,2)}</text><text x={w-r} y={h*4+24} textAnchor="end" className="tick">{fmt(x1,2)}</text><text x={w/2} y={h*4+40} textAnchor="middle">x (m)</text></svg>{tip&&<div className="tooltip" style={{left:`${Math.min(tip.x+14,700)}px`,top:`${Math.max(tip.y-52,24)}px`}}>x = {fmt(d[tip.i].x)} m<br/>平面 y = {fmt(d[tip.i].plan_y)} m<br/>立面 y = {fmt(d[tip.i].elevation_y)} m<br/>应力 = {fmt(d[tip.i].stress,1)} MPa<br/>累计伸长量 = {fmt(d[tip.i].elongation_mm,2)} mm</div>}</div></section>
}

function detailRows(result:CalculationResult){let left=result.left_elongation_mm,right=0;return result.segments.map((segment,index)=>{const cumulative=segment.source==="left"?left:right+segment.elongation_mm;if(segment.source==="left")left-=segment.elongation_mm;else right+=segment.elongation_mm;return {...segment,cumulative,balanceAfter:index>0&&result.segments[index-1].source!==segment.source}})}

export default function App(){const[e,setE]=useState(elevation),[p,setP]=useState(plan),[q,setQ]=useState({k:.0015,mu:.25,elastic_modulus:195000,left_stress:1395,right_stress:1395}),[res,setRes]=useState<CalculationResult|null>(null),[err,setErr]=useState(""),[busy,setBusy]=useState(false);const calc=async()=>{setBusy(true);setErr("");try{const r=await fetch(apiUrl("/api/calculate"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({elevation:e,plan:p,...q})}),b=await r.json();if(!r.ok)throw Error(b.detail||"计算失败");setRes(b)}catch(x){setErr(x instanceof Error?x.message:"计算失败")}finally{setBusy(false)}};return <main><header><b>TENDON MVP</b><h1>预应力钢束理论伸长量计算</h1><p>输入立面与平面线形，复核应力、不动点和理论伸长量。</p></header><DxfImportControl onImported={(nextElevation,nextPlan)=>{setE(nextElevation);setP(nextPlan);setRes(null);setErr("")}}/><div className="grid"><Editor title="立面线形" value={e} onChange={setE}/><Editor title="平面线形" value={p} onChange={setP}/></div><section className="panel"><div className="head"><div><h2>计算参数</h2><small>默认值仅用于快速计算，应按设计文件或者相关规范取值。</small></div><button className="primary" onClick={calc} disabled={busy}>{busy?"计算中…":"开始计算"}</button></div><div className="params">{([['k','孔道偏差系数 k'],['mu','摩阻系数 μ'],['elastic_modulus','钢束弹性模量 Ep（MPa）'],['left_stress','左端张拉应力（MPa）'],['right_stress','右端张拉应力（MPa）']] as const).map(([key,label])=><label key={key}>{label}<input type="text" inputMode="decimal" value={q[key]} onChange={event=>setQ({...q,[key]:Number(event.target.value)})}/></label>)}</div></section>{err&&<p className="error">{err}</p>}{res&&<><div className="metrics">{[['钢束总长',`${fmt(res.total_length)} m`],['不动点',res.balance_x===null?'—':`${fmt(res.balance_x)} m`],['左端伸长量',`${fmt(res.left_elongation_mm,2)} mm`],['右端伸长量',`${fmt(res.right_elongation_mm,2)} mm`],['总伸长量',`${fmt(res.total_elongation_mm,2)} mm`],['累计转角',`${fmt(res.total_turn,4)} rad`]].map(([a,b])=><div className="metric" key={a}><small>{a}</small><strong>{b}</strong></div>)}</div><Chart result={res}/><section className="panel"><h2>分段计算明细</h2><table><thead><tr><th>序号</th><th>伸长方向</th><th>x 起</th><th>x 终</th><th>长度</th><th>转角</th><th>平均应力</th><th>伸长量</th><th>累计伸长量</th></tr></thead><tbody>{detailRows(res).map((s,i)=><tr className={s.balanceAfter?"balance-start":""} key={i}><td>{i+1}</td><td>{s.source==='left'?'左端':'右端'}</td><td>{fmt(s.x_start)}</td><td>{fmt(s.x_end)}</td><td>{fmt(s.length)}</td><td>{fmt(s.turn,5)}</td><td>{fmt(s.average_stress,1)}</td><td>{fmt(s.elongation_mm,2)}</td><td>{fmt(s.cumulative,2)}</td></tr>)}</tbody></table></section></>}</main>}
