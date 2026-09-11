import React,{useState} from 'react';
import {Field,Empty,days,classes} from './ui';

export function MySchedule({me}){
 const lessons=me.details.lessons||[];
 const today=String((new Date().getDay()+6)%7);
 const [day,setDay]=useState(()=>lessons.some(row=>String(row.day)===today)?today:String(lessons[0]?.day??today));
 const selected=lessons.filter(row=>String(row.day)===day);
 const classrooms=classes.filter(classroom=>selected.some(row=>row.class===classroom));
 const times=[...new Set(selected.map(row=>`${row.start}–${row.end}`))].sort();
 const subjects=[...new Set(lessons.map(row=>row.subject))].sort((a,b)=>a.localeCompare(b,'pt-BR'));
 const color=subject=>{const hue=Math.round(subjects.indexOf(subject)*137.508)%360;return {backgroundColor:`hsl(${hue} 65% 92%)`,color:`hsl(${hue} 55% 25%)`,borderColor:`hsl(${hue} 45% 78%)`}};
 return <><div className="toolbar"><Field label="Dia da semana"><select value={day} onChange={e=>setDay(e.target.value)}>{days.map((name,index)=><option key={name} value={String(index)}>{name}</option>)}</select></Field></div>{selected.length?<section className="sheet table-wrap my-schedule" role="region" aria-label={`Grade pedagógica de ${days[Number(day)]}`} tabIndex={0}><table><caption className="sr-only">{days[Number(day)]}: horários, turmas e matérias</caption><thead><tr><th scope="col">Horário</th>{classrooms.map(classroom=><th scope="col" key={classroom}>{classroom}</th>)}</tr></thead><tbody>{times.map(time=><tr key={time}><th scope="row">{time}</th>{classrooms.map(classroom=><td key={classroom}>{selected.filter(row=>`${row.start}–${row.end}`===time&&row.class===classroom).map((row,index)=><span className="schedule-subject" style={color(row.subject)} key={index}>{row.subject}</span>)}</td>)}</tr>)}</tbody></table></section>:<section className="sheet"><Empty>{lessons.length?'Nenhuma aula cadastrada neste dia.':'Sua grade pedagógica ainda não foi cadastrada.'}</Empty></section>}</>;
}
