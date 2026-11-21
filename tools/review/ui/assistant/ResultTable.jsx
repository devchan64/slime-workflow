import React from "react";

export default function ResultTable({table}) {
  return <section><strong>{table.title}</strong><p>{table.summary}</p>
    <table aria-label={table.title}><thead><tr>
      {table.columns.map(column=><th key={column} scope="col">{column}</th>)}
    </tr></thead><tbody>
      {table.rows.map((row,index)=><tr key={index}>{row.map((value,i)=><td key={i}>{value}</td>)}</tr>)}
      {table.rows.length===0 && <tr><td colSpan={table.columns.length}>조회된 항목이 없습니다.</td></tr>}
    </tbody></table>
  </section>;
}
