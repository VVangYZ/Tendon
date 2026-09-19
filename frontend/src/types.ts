export type InputMode = "xyr" | "xyb";
export interface PointRow { x:number; y:number; value:number }
export interface ProfileInput { mode:InputMode; points:PointRow[] }
export interface DxfImportResponse { elevation:ProfileInput; plan:ProfileInput; unit:"m"|"mm" }
export interface DistributionPoint { x:number; plan_y:number; elevation_y:number; stress:number; elongation_mm:number }
export interface Segment { x_start:number; x_end:number; length:number; turn:number; average_stress:number; elongation_mm:number; source:string }
export interface CalculationResult { total_length:number; total_turn:number; total_elongation_mm:number; left_elongation_mm:number; right_elongation_mm:number; balance_x:number|null; distribution:DistributionPoint[]; segments:Segment[] }
export interface NamedProfile { id:string; points:PointRow[] }
export interface BatchDefaults { unit:"m"|"mm"; k:number; mu:number; elastic_modulus:number; left_stress:number; right_stress:number }
export interface BatchTendon { id:string; elevation_id:string; plan_id:string; left_stress:number; right_stress:number; k:number; mu:number; elastic_modulus:number; elevation:ProfileInput|null; plan:ProfileInput|null; status:"ready"|"invalid"; error:string|null }
export interface BatchProject { defaults:BatchDefaults; elevation_profiles:NamedProfile[]; plan_profiles:NamedProfile[]; tendons:BatchTendon[] }
export interface BatchImportResponse { project:BatchProject; ready_count:number; invalid_count:number }
export interface BatchCalculationItem { id:string; status:"success"|"failed"|"skipped"; error:string|null; result:CalculationResult|null }
export interface BatchCalculationResponse { items:BatchCalculationItem[]; success_count:number; failed_count:number }
