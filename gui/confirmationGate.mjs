// A confirmation can be consumed once; cancelling invalidates the same review.
export function createConfirmationGate(){
  let current=null;
  return {
    open(){current={};return current;},
    cancel(){current=null;},
    claim(token){if(!token || current!==token)return false;current=null;return true;},
  };
}
