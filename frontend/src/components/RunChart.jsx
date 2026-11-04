import {Bar,BarChart,CartesianGrid,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';

export default function RunChart({data}){
  return <ResponsiveContainer width="100%" height={110}>
    <BarChart data={data} margin={{top:5,right:2,left:-22,bottom:0}}>
      <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false}/>
      <XAxis dataKey="date" tick={{fontSize:8,fill:'var(--muted)'}} tickFormatter={x=>x.slice(5)} axisLine={false} tickLine={false}/>
      <YAxis tick={{fontSize:8,fill:'var(--muted)'}} axisLine={false} tickLine={false}/>
      <Tooltip contentStyle={{background:'var(--panel2)',border:'1px solid var(--line)',borderRadius:6,fontSize:10,color:'var(--text)'}}/>
      <Bar dataKey="runs" fill="var(--lime)" radius={[3,3,0,0]} maxBarSize={24}/>
    </BarChart>
  </ResponsiveContainer>
}
