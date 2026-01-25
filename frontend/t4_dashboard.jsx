import React, { useState, useEffect, useRef } from 'react';
import { Battery, Thermometer, Droplets, Zap, Sun, Moon, Power, Wifi, Bluetooth, Gauge } from 'lucide-react';

const Card = ({ children, className = "" }) => (
  <div className={`bg-gray-800 rounded-xl p-4 shadow-lg border border-gray-700 ${className}`}>
    {children}
  </div>
);

export default function App() {
  const [systemInfo, setSystemInfo] = useState({
    tempInside: 21.5,
    tempOutside: 14.2,
    humidity: 45,
    batterySoc: 88,
    batteryVoltage: 13.4,
    solarPower: 120,
    solarCurrent: 9.2,
    consumption: 45,
    pitch: 0,
    roll: 0,
  });

  const [activeTab, setActiveTab] = useState('dashboard');
  const [isSleeping, setIsSleeping] = useState(false);
  const idleTimer = useRef(null);
  const SLEEP_TIMEOUT = 1000 * 60 * 10; 

  const resetIdleTimer = () => {
    if (isSleeping) setIsSleeping(false);
    if (idleTimer.current) clearTimeout(idleTimer.current);
    idleTimer.current = setTimeout(() => setIsSleeping(true), SLEEP_TIMEOUT);
  };

  useEffect(() => {
    resetIdleTimer();
    window.addEventListener('click', resetIdleTimer);
    window.addEventListener('touchstart', resetIdleTimer);

    const interval = setInterval(() => {
      setSystemInfo(prev => ({
        ...prev,
        solarPower: prev.solarPower + (Math.random() * 10 - 5),
        pitch: prev.pitch + (Math.random() * 0.2 - 0.1),
      }));
    }, 2000);

    return () => {
      window.removeEventListener('click', resetIdleTimer);
      window.removeEventListener('touchstart', resetIdleTimer);
      clearInterval(interval);
      if (idleTimer.current) clearTimeout(idleTimer.current);
    };
  }, [isSleeping]);

  if (isSleeping) {
    return (
      <div className="w-full h-screen bg-black flex items-center justify-center cursor-pointer" onClick={resetIdleTimer}>
        <div className="text-gray-600 animate-pulse flex flex-col items-center">
          <Moon size={48} />
          <span className="mt-4 text-sm font-sans">Touch to wake</span>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full min-h-screen bg-gray-900 text-gray-100 font-sans p-4 overflow-hidden">
      <header className="flex justify-between items-center mb-6 px-2">
        <div className="flex items-center space-x-2">
          <div className="bg-blue-600 p-2 rounded-lg">
            <span className="font-bold text-xl tracking-wider text-white">MULTIVAN PI</span>
          </div>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-1 text-green-400"><Wifi size={18} /><span className="text-xs">Hotspot</span></div>
          <div className="flex items-center space-x-1 text-blue-400"><Bluetooth size={18} /><span className="text-xs">Victron</span></div>
          <div className="text-xl font-mono text-white">{new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
        </div>
      </header>

      <main className="grid grid-cols-1 md:grid-cols-12 gap-6 h-full pb-20">
        <nav className="md:col-span-2 fixed bottom-0 left-0 w-full md:relative bg-gray-800 md:bg-transparent border-t md:border-t-0 border-gray-700 p-4 md:p-0 flex md:flex-col justify-around md:justify-start md:space-y-6 z-50">
          <NavButton active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')} icon={<Gauge />} label="Cockpit" />
          <NavButton active={activeTab === 'leveling'} onClick={() => setActiveTab('leveling')} icon={<Zap />} label="Leveling" />
          <NavButton active={activeTab === 'climate'} onClick={() => setActiveTab('climate')} icon={<Thermometer />} label="Klima" />
        </nav>

        <div className="md:col-span-10 space-y-6">
          {activeTab === 'dashboard' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-gray-400 text-sm uppercase">Batterie</h3>
                  <Battery className="text-green-500" />
                </div>
                <div className="flex items-baseline space-x-2">
                  <span className="text-5xl font-bold">{systemInfo.batterySoc}%</span>
                  <span className="text-gray-400">{systemInfo.batteryVoltage} V</span>
                </div>
                <div className="mt-4 w-full bg-gray-700 h-2 rounded-full overflow-hidden">
                  <div className="bg-green-500 h-full transition-all duration-1000" style={{ width: `${systemInfo.batterySoc}%` }} />
                </div>
              </Card>
              <Card>
                <div className="flex justify-between items-start mb-4"><h3 className="text-gray-400 text-sm uppercase font-bold tracking-widest text-yellow-500">Solar</h3><Sun className="text-yellow-500" /></div>
                <div className="flex items-baseline space-x-2"><span className="text-5xl font-bold text-yellow-400">{Math.round(systemInfo.solarPower)}</span><span className="text-gray-400">Watt</span></div>
              </Card>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

const NavButton = ({ active, onClick, icon, label }) => (
  <button onClick={onClick} className={`flex md:flex-row flex-col items-center md:space-x-4 p-2 md:px-4 md:py-3 rounded-xl transition-all ${active ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' : 'text-gray-400 hover:bg-gray-800 hover:text-white'}`}>
    {React.cloneElement(icon, { size: 24 })}
    <span className="text-xs md:text-lg mt-1 md:mt-0 font-medium">{label}</span>
  </button>
);
