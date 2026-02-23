import React, { useState, useEffect, useRef, useMemo } from 'react';
import axios from 'axios';
import {
  Plus, Trash2, Save, Play, Clock, Link as LinkIcon,
  FileVideo, GripVertical, Search, Calendar, ChevronLeft, ChevronRight, Info, ZoomIn, ZoomOut, Maximize2
} from 'lucide-react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import {
  format, addDays, startOfWeek, endOfWeek,
  eachDayOfInterval, isSameDay, parseISO
} from 'date-fns';

const API_BASE = 'http://127.0.0.1:5000/api';

function App() {
  const [schedule, setSchedule] = useState([]);
  const [library, setLibrary] = useState([]);
  const [status, setStatus] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [enabled, setEnabled] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [hourHeight, setHourHeight] = useState(180);

  const minuteHeight = hourHeight / 60;

  useEffect(() => {
    fetchSchedule();
    fetchLibrary();
    const animation = requestAnimationFrame(() => setEnabled(true));
    return () => {
      cancelAnimationFrame(animation);
      setEnabled(false);
    };
  }, []);

  const fetchSchedule = async () => {
    try {
      const res = await axios.get(`${API_BASE}/schedule`);
      const data = res.data.map((item, idx) => ({
        ...item,
        id: `sched-${idx}-${Date.now()}-${Math.random()}`
      }));
      setSchedule(data);
    } catch (err) {
      console.error("Error fetching schedule", err);
      setStatus('Offline');
    }
  };

  const fetchLibrary = async () => {
    try {
      const res = await axios.get(`${API_BASE}/videos`);
      const data = res.data.map((v, i) => ({
        ...v,
        libId: `lib-${i}-${Math.random()}`
      }));
      setLibrary(data);
    } catch (err) {
      console.error("Error fetching library", err);
    }
  };

  const timeToMinutes = (timeStr) => {
    if (!timeStr) return 0;
    const [h, m] = timeStr.split(':').map(Number);
    return (h || 0) * 60 + (m || 0);
  };

  const minutesToTime = (minutes) => {
    const h = Math.floor(minutes / 60) % 24;
    const m = Math.floor(minutes % 60);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  };

  const durationToMinutes = (durationStr) => {
    if (!durationStr) return 30;
    const parts = durationStr.split(':').map(Number);
    if (parts.length === 3) return parts[0] * 60 + parts[1] + parts[2] / 60;
    if (parts.length === 2) return parts[0] + parts[1] / 60;
    return parseFloat(durationStr) || 30;
  };

  // GLOBAL GAPLESS PROCESSING WITH CROSS-DAY SPILLOVER
  const processedSchedule = useMemo(() => {
    // 1. Sort globally
    const sorted = [...schedule].sort((a, b) => {
      if (a.date !== b.date) return a.date.localeCompare(b.date);
      return timeToMinutes(a.startTime) - timeToMinutes(b.startTime);
    });

    const dayToAbs = (dateStr) => {
      const d = parseISO(dateStr);
      return Math.floor(d.getTime() / 60000);
    };

    const calculationResult = [];
    let lastEndAbs = 0;

    sorted.forEach(item => {
      const intendedAbs = dayToAbs(item.date) + timeToMinutes(item.startTime);
      // Real start is whichever is LATER: intended drop time OR the previous video's end
      const startAbs = Math.max(intendedAbs, lastEndAbs);
      const durationMin = durationToMinutes(item.duration);
      const endAbs = startAbs + durationMin;

      const startDateObj = new Date(startAbs * 60000);
      calculationResult.push({
        ...item,
        actualDate: format(startDateObj, 'yyyy-MM-dd'),
        actualStartTime: format(startDateObj, 'HH:mm'),
        absStart: startAbs,
        absEnd: endAbs,
        durationMin
      });

      lastEndAbs = endAbs;
    });

    const visualBlocks = [];
    calculationResult.forEach(item => {
      const dayStartAbs = dayToAbs(item.actualDate);
      const nextDayStartAbs = dayStartAbs + 1440;

      // Part 1: Today
      const part1EndAbs = Math.min(item.absEnd, nextDayStartAbs);
      visualBlocks.push({
        ...item,
        uiDate: item.actualDate,
        uiStart: item.absStart - dayStartAbs,
        uiEnd: part1EndAbs - dayStartAbs,
        isGhost: false
      });

      // Part 2+: Midnight Spillover (if 24h+ spans multiple days recursively)
      let currentOverflowStart = nextDayStartAbs;
      while (currentOverflowStart < item.absEnd) {
        const overflowDateStr = format(new Date(currentOverflowStart * 60000), 'yyyy-MM-dd');
        const overflowDayEnd = currentOverflowStart + 1440;
        const partEnd = Math.min(item.absEnd, overflowDayEnd);

        visualBlocks.push({
          ...item,
          id: `${item.id}-ghost-${currentOverflowStart}`,
          uiDate: overflowDateStr,
          uiStart: 0,
          uiEnd: partEnd - currentOverflowStart,
          isGhost: true,
          originalId: item.id
        });
        currentOverflowStart = overflowDayEnd;
      }
    });

    return visualBlocks;
  }, [schedule]);

  const weekDays = useMemo(() => {
    const start = startOfWeek(currentDate, { weekStartsOn: 1 });
    return eachDayOfInterval({ start, end: addDays(start, 6) });
  }, [currentDate]);

  const onDragEnd = (result) => {
    const { source, destination, draggableId } = result;
    if (!destination) return;
    if (destination.droppableId === 'library') return;

    const [destDate, destHourStr] = destination.droppableId.split('__');
    const destHour = parseInt(destHourStr);
    const dropStartTime = `${String(destHour).padStart(2, '0')}:00`;

    let newSchedule = Array.from(schedule);
    let movedItem;

    if (source.droppableId === 'library') {
      const libItem = library.find(v => v.libId === draggableId);
      if (!libItem) return;
      movedItem = {
        ...libItem,
        id: `sched-${Date.now()}-${Math.random()}`,
        date: destDate,
        startTime: dropStartTime
      };
      delete movedItem.libId;
      newSchedule.push(movedItem);
    } else {
      const index = newSchedule.findIndex(i => i.id === draggableId);
      if (index === -1) return;
      [movedItem] = newSchedule.splice(index, 1);
      movedItem.date = destDate;
      movedItem.startTime = dropStartTime;
      newSchedule.push(movedItem);
    }
    setSchedule(newSchedule);
  };

  const handleSave = async () => {
    try {
      setStatus('Publishing...');
      // Use unique original items with their NEW calculated Dates/Times
      const seen = new Set();
      const toSave = [];

      processedSchedule.forEach(item => {
        const rootId = item.originalId || item.id;
        if (!seen.has(rootId)) {
          seen.add(rootId);
          toSave.push({
            name: item.name,
            link: item.link,
            duration: item.duration,
            date: item.actualDate,
            startTime: item.actualStartTime
          });
        }
      });

      toSave.sort((a, b) => {
        if (a.date !== b.date) return a.date.localeCompare(b.date);
        return timeToMinutes(a.startTime) - timeToMinutes(b.startTime);
      });

      await axios.post(`${API_BASE}/schedule`, toSave);
      setStatus('Success!');
      setTimeout(() => setStatus(''), 3000);
      fetchSchedule();
    } catch (err) {
      setStatus('Error');
    }
  };

  const handleRemove = (id) => {
    setSchedule(schedule.filter(item => item.id !== id));
    if (selectedItem?.id === id) setSelectedItem(null);
  };

  if (!enabled) return null;

  return (
    <div className="h-screen bg-slate-950 text-slate-100 flex flex-col font-sans overflow-hidden antialiased">
      <DragDropContext onDragEnd={onDragEnd}>

        <header className="px-8 py-5 flex items-center justify-between bg-slate-900 border-b border-white/5 shrink-0 z-50">
          <div className="flex items-center gap-10">
            <div className="flex items-center gap-4 cursor-pointer" onClick={() => window.location.reload()}>
              <div className="bg-blue-600 p-2.5 rounded-[1.2rem] shadow-xl shadow-blue-500/10">
                <Play className="text-white w-6 h-6 fill-current" />
              </div>
              <h1 className="text-xl font-black italic tracking-tighter text-white uppercase">ULTRA TV</h1>
            </div>

            <div className="flex bg-slate-800 p-1 rounded-2xl border border-white/5">
              <button onClick={() => setCurrentDate(addDays(currentDate, -7))} className="p-2.5 hover:bg-slate-700 rounded-xl transition-all text-slate-400 group"><ChevronLeft size={18} className="group-hover:text-white" /></button>
              <button onClick={() => setCurrentDate(new Date())} className="px-5 text-[10px] font-black uppercase tracking-widest hover:bg-slate-700 rounded-xl transition-all">Today</button>
              <button onClick={() => setCurrentDate(addDays(currentDate, 7))} className="p-2.5 hover:bg-slate-700 rounded-xl transition-all text-slate-400 group"><ChevronRight size={18} className="group-hover:text-white" /></button>
            </div>

            <div className="flex items-center gap-4 bg-slate-800/50 px-5 py-2.5 rounded-2xl border border-white/5">
              <ZoomOut size={14} className="opacity-40" />
              <input
                type="range" min="60" max="400" value={hourHeight}
                onChange={(e) => setHourHeight(parseInt(e.target.value))}
                className="w-32 accent-blue-600 cursor-pointer h-1.5 rounded-lg appearance-none bg-slate-700"
              />
              <ZoomIn size={14} className="opacity-40" />
              <span className="text-[10px] font-black opacity-20 uppercase tracking-widest ml-1">{Math.round((hourHeight / 180) * 100)}%</span>
            </div>
          </div>

          <div className="flex items-center gap-8">
            {status && <span className="text-[11px] font-black uppercase text-blue-400 tracking-widest bg-blue-500/10 px-4 py-2 rounded-full border border-blue-500/20">{status}</span>}
            <button onClick={handleSave} className="bg-white hover:bg-blue-600 hover:text-white text-slate-900 px-10 py-3.5 rounded-full text-[10px] font-black uppercase tracking-[0.2em] transition-all active:scale-95 flex items-center gap-3">
              <Save size={16} />
              Publish Schedule
            </button>
          </div>
        </header>

        <div className="flex-1 flex overflow-hidden">
          <aside className="w-80 bg-slate-900 border-r border-white/5 flex flex-col shrink-0 overflow-hidden">

            <div className="p-6 bg-slate-950 border-b border-white/5 shrink-0 relative z-10">
              <h3 className="text-[10px] font-black uppercase opacity-20 tracking-[0.3em] mb-4 flex items-center gap-2">
                <Maximize2 size={12} /> Video Details
              </h3>
              <div className={`transition-all duration-300`}>
                {selectedItem ? (
                  <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2">
                    <div className="p-5 bg-blue-600 rounded-3xl border border-blue-400/30">
                      <p className="text-[10px] font-black uppercase text-white/40 tracking-widest mb-2">Selected Asset</p>
                      <p className="text-[16px] font-black leading-[1.2] text-white mb-6 break-words">{selectedItem.name}</p>
                      <div className="grid grid-cols-2 gap-4 pt-5 border-t border-white/10">
                        <div>
                          <p className="text-[9px] uppercase font-black text-white/40 tracking-wider mb-1">Actual Start</p>
                          <p className="text-sm font-black text-white">{selectedItem.actualStartTime}</p>
                        </div>
                        <div>
                          <p className="text-[9px] uppercase font-black text-white/40 tracking-wider mb-1">Duration</p>
                          <p className="text-sm font-black text-white">{selectedItem.duration}</p>
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleRemove(selectedItem.originalId || selectedItem.id)}
                        className="flex-1 py-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-500 text-[10px] font-black uppercase tracking-widest hover:bg-red-500 hover:text-white transition-all flex items-center justify-center gap-2"
                      >
                        <Trash2 size={14} /> Delete
                      </button>
                      <button
                        onClick={() => setSelectedItem(null)}
                        className="px-4 py-4 rounded-2xl bg-slate-800 text-slate-400 hover:text-white transition-all border border-white/5"
                      >
                        Close
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="py-12 flex flex-col items-center justify-center text-center px-8 border-2 border-dashed border-white/5 rounded-[2.5rem] opacity-40">
                    <div className="p-4 bg-slate-800 rounded-full mb-4">
                      <Clock size={24} className="opacity-50" />
                    </div>
                    <p className="text-[10px] font-black leading-relaxed uppercase tracking-[0.1em]">Select a video in the grid to view details</p>
                  </div>
                )}
              </div>
            </div>

            <div className="flex-1 flex flex-col overflow-hidden bg-slate-900/50">
              <div className="p-6 pb-2">
                <h3 className="text-[10px] font-black uppercase opacity-20 tracking-[0.3em] mb-4">Master Library</h3>
                <div className="relative group mb-4">
                  <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 opacity-20 group-focus-within:opacity-100 transition-opacity" />
                  <input
                    placeholder="Find videos..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full bg-slate-950 border border-white/5 rounded-2xl pl-12 pr-5 py-5 text-sm outline-none focus:border-blue-500 transition-all font-bold placeholder:opacity-20 shadow-inner"
                  />
                </div>
              </div>

              <Droppable droppableId="library" isDropDisabled={true}>
                {(provided) => (
                  <div {...provided.droppableProps} ref={provided.innerRef} className="flex-1 overflow-y-auto p-6 pt-2 space-y-4 custom-scrollbar">
                    {library.filter(v => v.name.toLowerCase().includes(searchTerm.toLowerCase())).map((item, index) => (
                      <Draggable key={item.libId} draggableId={item.libId} index={index}>
                        {(provided, snapshot) => (
                          <div
                            ref={provided.innerRef}
                            {...provided.draggableProps}
                            {...provided.dragHandleProps}
                            className={`p-6 rounded-[2.2rem] border-2 transition-all select-none group shadow-sm ${snapshot.isDragging
                              ? 'bg-blue-600 border-blue-400 scale-110 z-[9999] rotate-2'
                              : 'bg-slate-900 border-white/5 hover:border-blue-500/50 hover:bg-slate-800'
                              }`}
                          >
                            <p className="font-black text-[13px] leading-tight mb-2 truncate">{item.name}</p>
                            <div className="flex justify-between items-center text-[9px] font-mono tracking-widest opacity-30 uppercase">
                              <span>{item.duration}</span>
                              <GripVertical size={14} className="opacity-10" />
                            </div>
                          </div>
                        )}
                      </Draggable>
                    ))}
                    {provided.placeholder}
                  </div>
                )}
              </Droppable>
            </div>
          </aside>

          <main className="flex-1 flex flex-col overflow-hidden bg-slate-950 relative">
            <div className="flex-1 overflow-auto custom-scrollbar relative bg-slate-950">
              <div className="w-fit min-w-full flex flex-col">
                {/* STICKY WEEK HEADER */}
                <div className="flex bg-slate-900 border-b border-white/5 sticky top-0 z-50 w-full min-w-max">
                  <div className="w-20 shrink-0 border-r border-white/10 bg-slate-900 flex items-center justify-center sticky left-0 z-[60]">
                    <Clock size={16} className="text-slate-800" />
                  </div>
                  {weekDays.map(day => (
                    <div key={day.toString()} className={`flex-1 p-6 text-center border-r border-white/10 last:border-r-0 min-w-[220px] ${isSameDay(day, new Date()) ? 'bg-blue-600/5' : ''}`}>
                      <p className="text-[10px] uppercase font-black opacity-20 mb-2 tracking-[0.4em]">{format(day, 'EEEE')}</p>
                      <p className={`text-4xl font-black tracking-tighter ${isSameDay(day, new Date()) ? 'text-blue-500' : 'text-slate-300'}`}>{format(day, 'dd')}</p>
                    </div>
                  ))}
                </div>

                <div className="flex relative w-fit min-w-full" style={{ height: 24 * hourHeight }}>
                  {/* TIME AXIS */}
                  <div className="w-20 border-r border-white/10 sticky left-0 bg-slate-950/95 backdrop-blur-xl z-30 shrink-0 select-none">
                    {[...Array(24)].map((_, h) => (
                      <div key={h} style={{ height: hourHeight }} className="border-b border-white/5 flex flex-col items-center justify-center opacity-40">
                        <span className="text-[13px] font-black text-slate-500">{String(h).padStart(2, '0')}:00</span>
                        <div className="w-1.5 h-1.5 bg-slate-800 rounded-full mt-4"></div>
                      </div>
                    ))}
                  </div>

                  {/* COLUMNS */}
                  {weekDays.map(day => {
                    const dayStr = format(day, 'yyyy-MM-dd');
                    const dayItems = processedSchedule.filter(item => item.uiDate === dayStr);

                    return (
                      <div key={dayStr} className={`flex-1 border-r border-white/10 relative min-w-[220px] ${isSameDay(day, new Date()) ? 'bg-blue-600/[0.02]' : ''}`}>
                        <div className="absolute inset-0 pointer-events-none z-0">
                          {[...Array(24)].map((_, h) => (
                            <div key={h} style={{ height: hourHeight }} className="border-b border-white/[0.03] last:border-b-0"></div>
                          ))}
                        </div>

                        <div className="relative h-full z-10">
                          {[...Array(24)].map((_, h) => (
                            <Droppable key={`${dayStr}__${h}`} droppableId={`${dayStr}__${h}`}>
                              {(provided, snapshot) => (
                                <div
                                  {...provided.droppableProps}
                                  ref={provided.innerRef}
                                  style={{ height: hourHeight }}
                                  className={`w-full relative transition-all ${snapshot.isDraggingOver ? 'bg-blue-600/10 border-2 border-blue-500/20 z-10 rounded-2xl' : ''
                                    }`}
                                >
                                  {dayItems
                                    .filter(item => Math.floor(item.uiStart / 60) === h)
                                    .map((item, index) => {
                                      const topPos = (item.uiStart % 60) * minuteHeight;
                                      const heightPx = (item.uiEnd - item.uiStart) * minuteHeight;
                                      const isTiny = heightPx < 45;
                                      const isSelected = selectedItem?.id === item.id;

                                      return (
                                        <Draggable
                                          key={item.id}
                                          draggableId={item.id}
                                          index={index}
                                          isDragDisabled={item.isGhost}
                                        >
                                          {(p, s) => (
                                            <div
                                              ref={p.innerRef}
                                              {...p.draggableProps}
                                              {...p.dragHandleProps}
                                              onClick={() => setSelectedItem(item)}
                                              style={{
                                                ...p.draggableProps.style,
                                                position: 'absolute',
                                                top: topPos,
                                                height: Math.max(heightPx, 6),
                                                left: 6,
                                                right: 6,
                                                zIndex: (s.isDragging || isSelected) ? 999 : 20,
                                                opacity: item.isGhost ? 0.7 : 1
                                              }}
                                              className={`rounded-2xl border-2 transition-all ${s.isDragging
                                                ? 'bg-blue-600 border-blue-400 z-[9999] opacity-90 cursor-grabbing'
                                                : isSelected
                                                  ? 'bg-yellow-400 border-yellow-500 z-40 text-slate-900 shadow-[0_0_40px_rgba(250,204,21,0.3)]'
                                                  : 'bg-white border-white hover:bg-slate-50 cursor-pointer text-slate-900 shadow-sm'
                                                }`}
                                            >
                                              {!isTiny && (
                                                <div className={`p-4 h-full flex flex-col justify-between ${s.isDragging ? 'text-white' : 'text-slate-900'} relative`}>
                                                  <div className="flex flex-col gap-1 min-w-0">
                                                    <span className={`text-[9px] font-black uppercase tracking-tighter opacity-40`}>
                                                      {item.isGhost ? 'Spillover' : item.actualStartTime}
                                                    </span>
                                                    <p className="text-[13px] font-black leading-tight break-words line-clamp-3">
                                                      {item.name}
                                                      {item.isGhost && <span className="ml-2 opacity-30 text-[10px] italic">(cont.)</span>}
                                                    </p>
                                                  </div>
                                                </div>
                                              )}
                                            </div>
                                          )}
                                        </Draggable>
                                      );
                                    })}
                                  {provided.placeholder}
                                </div>
                              )}
                            </Droppable>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </main>
        </div>
      </DragDropContext>
    </div>
  );
}

export default App;
