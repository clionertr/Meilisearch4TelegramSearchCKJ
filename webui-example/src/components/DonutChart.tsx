import React from 'react';

interface DonutChartProps {
    percentage: number;
    color: string;
    bgColor: string;
}

const DonutChart: React.FC<DonutChartProps> = ({ percentage, color, bgColor }) => {
    // We use a conic gradient to simulate the donut chart as seen in the HTML reference
    const style = {
        background: `conic-gradient(${color} 0% ${percentage}%, ${bgColor} ${percentage}% 100%)`,
    };

    return (
        <div 
            className="rounded-full w-[120px] h-[120px] relative flex items-center justify-center"
            style={style}
        >
            <div className="w-[80px] h-[80px] bg-[#192d33] rounded-full absolute flex flex-col items-center justify-center z-10">
                <span className="text-xl font-bold block text-white">{percentage}%</span>
                <span className="text-[10px] text-slate-400 uppercase">Used</span>
            </div>
        </div>
    );
};

export default DonutChart;