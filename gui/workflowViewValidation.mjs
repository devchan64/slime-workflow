export function validWorkflowView(value,run){
  const record=item=>item!==null && typeof item==="object" && !Array.isArray(item);
  const optionalString=item=>item==null || typeof item==="string";
  const validBindings=item=>item==null || (record(item) && Object.values(item).every(binding=>record(binding) && typeof binding.from_step==="string" && typeof binding.output==="string"));
  return record(value) && value.run_id===run && Array.isArray(value.steps) && value.steps.every(step=>record(step) && typeof step.step_id==="string" && typeof step.state==="string" && optionalString(step.cancel_delivery) && optionalString(step.block_reason) && validBindings(step.bindings)) &&
    Array.isArray(value.results) && value.results.every(result=>record(result) && typeof result.step_id==="string" && typeof result.job_id==="string" && typeof result.attempt_id==="string" && record(result.outputs)) &&
    Array.isArray(value.choices) && value.choices.every(choice=>record(choice) && [choice.step_id,choice.input_field,choice.source_request,choice.digest].every(item=>typeof item==="string") && [true,false,0,1].includes(choice.selected)) &&
    Array.isArray(value.retries) && value.retries.every(retry=>record(retry) && [retry.step_id,retry.source_request,retry.source_run,retry.retry_run].every(item=>typeof item==="string"));
}
