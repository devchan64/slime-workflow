export function formatActivityOutput(output){
  if(typeof output!=="string" || output.length>100000)return "";
  let formatted="";
  try{
    const value=JSON.parse(output);
    if(value && typeof value==="object"){
      let depth=0,inString=false,escaped=false;
      for(const char of output){
        if(inString){formatted+=char;if(escaped)escaped=false;else if(char==="\\")escaped=true;else if(char==='"')inString=false;continue;}
        if(char==='"'){inString=true;formatted+=char;}
        else if(char==="{" || char==="["){depth++;if(depth>100)return "";formatted+=char+"\n"+"  ".repeat(depth);}
        else if(char==="}" || char==="]"){depth--;formatted+="\n"+"  ".repeat(depth)+char;}
        else if(char===",")formatted+=",\n"+"  ".repeat(depth);
        else if(char===":")formatted+=": ";
        else if(!/\s/.test(char))formatted+=char;
      }
    }
  }catch{formatted="";}
  return formatted;
}
