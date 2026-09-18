export type InputMode = "xyr" | "xyb";
export interface PointRow { x:number; y:number; value:number }
export interface ProfileInput { mode:InputMode; points:PointRow[] }
export interface DxfImportResponse { elevation:ProfileInput; plan:ProfileInput; unit:"m"|"mm" }
export interface DistributionPoint { x:number; plan_y:number; elevation_y:number; stress:number; elongation_mm:number }
export interface Segment { x_start:number; x_end:number; length:number; turn:number; average_stress:number; elongation_mm:number; source:string }
export interface CalculationResult { total_length:number; total_turn:number; total_elongation_mm:number; left_elongation_mm:number; right_elongation_mm:number; balance_x:number|null; distribution:DistributionPoint[]; segments:Segment[] }
