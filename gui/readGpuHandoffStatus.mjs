import {untilAborted} from './managementCommand.js';
import {validateGpuHandoffStatus} from './validateGpuHandoffStatus.mjs';

export async function readGpuHandoffStatus(command,session,id,service,signal){
  return executeGpuHandoffCommand(command,'hermes-gpu-handoff-status',{session_id:session,request_id:id},session,id,service,signal);
}

export async function executeGpuHandoffCommand(command,operation,payload,session,id,service,signal){
  const value=await untilAborted(command('hermes-agent',operation,payload,{signal}),signal);
  return validateGpuHandoffStatus(value,session,id,service);
}
