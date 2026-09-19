import { useState } from "react";
import SingleApp from "./App";
import BatchWorkspace from "./BatchWorkspace";

export default function Workspace(){
 const [mode,setMode]=useState<"single"|"batch">("single");
 return <><nav className="workspace-switch"><button className={mode==="single"?"active":""} onClick={()=>setMode("single")}>单根手动计算</button><button className={mode==="batch"?"active":""} onClick={()=>setMode("batch")}>多根批量计算</button></nav>{mode==="single"?<SingleApp/>:<BatchWorkspace/>}</>;
}
