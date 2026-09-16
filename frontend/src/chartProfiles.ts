import type { ProfileInput } from "./types";

let profiles: Record<string, ProfileInput> = {};
export const rememberProfile=(title:string,profile:ProfileInput)=>{profiles={...profiles,[title]:profile}};
export const getProfile=(title:string)=>profiles[title];
