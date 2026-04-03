"use client";

import { useState, useEffect, useRef } from "react";
import { Upload, Video, Wand2, Scissors, CheckCircle, Clock, Link as LinkIcon, FileVideo } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface WordData {
  word: string;
  start_time: number;
  end_time: number;
}

interface ClipData {
  title: string;
  description: string;
  hashtags: string;
  score: number;
  words?: WordData[];
}

interface Project {
  id: string;
  title: string;
  status: string;
  clips?: number;
  date: string;
  progress?: number;
  message?: string;
  sourceUrl?: string;
  clips_urls?: string[];
  clips_data?: ClipData[];
}

function ClipVideoPlayer({ 
  src, 
  wordsData, 
  apiBaseUrl 
}: { 
  src: string; 
  wordsData?: WordData[]; 
  apiBaseUrl: string; 
}) {
  const [currentTime, setCurrentTime] = useState(0);

  // TikTok style 1-word or 3-word bursts based on timing
  const activeWordIndex = wordsData ? wordsData.findIndex(w => currentTime >= w.start_time && currentTime <= w.end_time) : -1;
  
  return (
    <div className="w-full h-full relative">
      <video 
        className="w-full h-full object-contain"
        src={src.startsWith("http") ? src : `${apiBaseUrl}${src}`}
        controls
        loop
        playsInline
        onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
      />
      
      {/* Dynamic Subtitle Overlay Engine */}
      {wordsData && activeWordIndex !== -1 && (
        <div className="absolute top-1/2 left-0 w-full transform -translate-y-1/2 flex items-center justify-center pointer-events-none px-6 text-center z-10 transition-all duration-75">
          <span 
             className="text-4xl lg:text-5xl font-black text-yellow-400 italic tracking-tight scale-110 drop-shadow-[0_5px_5px_rgba(0,0,0,1)] uppercase"
             style={{ WebkitTextStroke: '2.5px black' }}
          >
             {wordsData[activeWordIndex].word}
          </span>
        </div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const [isUploading, setIsUploading] = useState(false);
  const [url, setUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  
  const [uploadMode, setUploadMode] = useState<"url" | "file">("url");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Dynamically attach to the correct IP so Mobile Phones don't try to query their own 127.0.0.1!
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" ? `http://${window.location.hostname}:8001` : "http://127.0.0.1:8001");
  
  const [projects, setProjects] = useState<Project[]>([
    { id: "proj_1", title: "My 2 Hour Podcast Episode", status: "completed", clips: 12, date: "2 hrs ago", sourceUrl: "https://www.youtube.com/watch?v=dQw4w9WgXcQ" },
    { id: "proj_2", title: "Twitch VOD - Tech Review", status: "processing", progress: 65, date: "Just now" },
    { id: "proj_3", title: "Startup Pitch Desk", status: "completed", clips: 4, date: "Yesterday" }
  ]);

  const getYouTubeId = (url: string) => {
    if (!url) return null;
    const match = url.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([^&?]+)/);
    return match ? match[1] : null;
  };

  // Initial Fetch
  useEffect(() => {
    fetch(`${apiBaseUrl}/api/v1/projects`)
      .then(res => res.json())
      .then(data => {
        const realProjects = Object.entries(data).map(([id, proj]: [string, any]) => ({
          id,
          title: proj.title || (proj.sourceUrl === "Local File" ? "Local Upload" : `Video: ${proj.sourceUrl?.substring(0, 20)}...`),
          status: proj.status,
          progress: proj.progress,
          clips: proj.clips,
          message: proj.message,
          date: "Recently",
          sourceUrl: proj.sourceUrl,
          clips_urls: proj.clips_urls,
          clips_data: proj.clips_data
        }));
        setProjects(curr => {
          // Merge real projects with mock projects for a full list
          const existingIds = new Set(realProjects.map(p => p.id));
          const mocks = curr.filter(p => p.id.startsWith("proj_") && !existingIds.has(p.id));
          return [...realProjects, ...mocks];
        });
      })
      .catch(e => console.error("Initial fetch error:", e));
  }, []);

  // Real Polling to FastAPI Backend
  useEffect(() => {
    const interval = setInterval(() => {
      setProjects((currentProjects) => {
        currentProjects.forEach((proj) => {
          if (proj.status === "processing") {
            // Only poll real projects 
            if (!proj.id.startsWith("proj_")) {
              fetch(`${apiBaseUrl}/api/v1/projects/${proj.id}/status`)
                .then(res => res.json())
                .then(data => {
                  setProjects(curr => curr.map(p => 
                    p.id === proj.id ? { 
                      ...p, 
                      title: data.title || p.title,
                      status: data.status, 
                      progress: data.progress, 
                      message: data.message || p.message,
                      clips: data.clips || 3,
                      clips_urls: data.clips_urls || p.clips_urls,
                      clips_data: data.clips_data || p.clips_data
                    } : p
                  ));
                }).catch(e => console.error("Polling error", e));
            } else {
               // Fake visual progress for the mock demo projects
               const newProgress = Math.min((proj.progress || 0) + 1, 100);
               if (newProgress >= 100) {
                 setProjects(curr => curr.map(p => p.id === proj.id ? { ...p, progress: 100, status: "completed", clips: 3 } : p));
               } else {
                 setProjects(curr => curr.map(p => p.id === proj.id ? { ...p, progress: newProgress } : p));
               }
            }
          }
        });
        return currentProjects;
      });
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  // We no longer need JS to handle the export! We will use a pure native anchor tag.

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleGenerate = async () => {
    if (uploadMode === "url" && !url) {
      alert("Please enter a YouTube URL.");
      return;
    }
    if (uploadMode === "file" && !selectedFile) {
      alert("Please select a video file from your device.");
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      let response;
      if (uploadMode === "file") {
        const formData = new FormData();
        formData.append("file", selectedFile as File);
        
        response = await fetch(`${apiBaseUrl}/api/v1/projects/upload`, {
          method: "POST",
          body: formData,
        });
      } else {
        response = await fetch(`${apiBaseUrl}/api/v1/projects/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url })
        });
      }
      
      if (response.ok) {
        const data = await response.json();
        // Add the new project to the top of our list
        setProjects([
          { 
            id: data.project_id, 
            title: uploadMode === "url" ? `New Video: ${url.substring(0, 25)}...` : `Local File: ${selectedFile!.name}`, 
            status: "processing", 
            progress: 0, 
            date: "Just now",
            clips: 0,
            sourceUrl: uploadMode === "url" ? url : "Local Upload"
          },
          ...projects
        ]);
        setIsUploading(false);
        setUrl("");
        setSelectedFile(null);
      } else {
        alert("Failed to queue video. Is the FastAPI backend running?");
      }
    } catch (error) {
      console.error(error);
      alert("Could not connect to the Backend API. Please ensure it is running.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen p-8 lg:p-12 relative">
      <div className="absolute top-0 left-0 w-full h-96 bg-gradient-to-br from-violet-900/20 via-fuchsia-900/10 to-transparent blur-3xl -z-10" />

      {/* Header */}
      <header className="flex justify-between items-center mb-16">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-violet-600 rounded-xl neon-glow">
            <Scissors className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
            AI Shorts Orchestrator
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="px-4 py-2 glass-panel rounded-full text-sm font-medium text-gray-300">
            ⚡ 240 mins remaining
          </div>
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-violet-500 to-fuchsia-500 border-2 border-zinc-800" />
        </div>
      </header>

      {/* Main Action Area */}
      <section className="mb-16">
        <div className="max-w-4xl mx-auto text-center mb-10">
          <h2 className="text-4xl lg:text-5xl font-extrabold tracking-tight mb-4">
            Turn long videos into <span className="text-violet-500">viral shorts.</span>
          </h2>
          <p className="text-lg text-gray-400">
            Upload your podcast or paste a YouTube link. Our AI will automatically find the hooks, crop the faces, and add Hormozi-style captions.
          </p>
        </div>

        <motion.div 
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          onClick={() => setIsUploading(true)}
          className="max-w-2xl mx-auto glass-panel border-dashed border-2 hover:border-violet-500 rounded-3xl p-12 text-center cursor-pointer transition-all duration-300 group relative overflow-hidden"
        >
          <div className="absolute inset-0 bg-violet-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative z-10 flex flex-col items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-zinc-800/50 flex items-center justify-center group-hover:bg-violet-600/20 transition-colors">
              <Upload className="w-8 h-8 text-violet-400" />
            </div>
            <div>
              <h3 className="text-xl font-bold mb-2">Drag & Drop your video</h3>
              <p className="text-gray-400 text-sm">MP4, MOV, or paste a YouTube URL directly.</p>
            </div>
            <button className="mt-4 px-6 py-3 bg-violet-600 hover:bg-violet-500 text-white rounded-full font-medium transition-colors">
              Paste Link or Select File
            </button>
          </div>
        </motion.div>
      </section>

      {/* Recent Projects Grid */}
      <section>
        <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
          <Clock className="w-5 h-5 text-gray-400" />
          Recent Projects
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((proj, i) => (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              key={proj.id} 
              className="glass-panel p-6 rounded-2xl hover:bg-zinc-800/80 transition-colors group cursor-pointer"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="p-3 bg-zinc-800 rounded-lg group-hover:bg-zinc-700 transition">
                  <Video className="w-5 h-5 text-gray-300" />
                </div>
                {proj.status === "completed" ? (
                  <span className="flex items-center gap-1 text-xs font-semibold text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded-full">
                    <CheckCircle className="w-3 h-3" /> Ready
                  </span>
                ) : proj.status === "failed" ? (
                  <span className="flex items-center gap-1 text-xs font-semibold text-red-400 bg-red-400/10 px-2 py-1 rounded-full">
                    ✕ Failed
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-xs font-semibold text-amber-400 bg-amber-400/10 px-2 py-1 rounded-full whitespace-nowrap overflow-hidden text-ellipsis max-w-[200px]">
                    <Wand2 className="w-3 h-3 animate-pulse" /> {proj.message || `Processing ${proj.progress}%`}
                  </span>
                )}
              </div>
              
              <h4 className="font-semibold text-lg truncate mb-1">{proj.title}</h4>
              <p className="text-xs text-gray-500 mb-4">{proj.date}</p>
              
              {proj.status === "completed" && (
                <div className="flex items-center justify-between border-t border-zinc-800 pt-4 mt-2">
                  <span className="text-sm text-gray-400">{proj.clips} clips generated</span>
                  <button 
                    onClick={() => setActiveProject(proj)}
                    className="text-sm text-violet-400 font-medium hover:text-violet-300 transition-colors"
                  >
                    View & Edit →
                  </button>
                </div>
              )}
              
              {proj.status === "processing" && (
                <div className="mt-6 h-1 w-full bg-zinc-800 rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: "0%" }}
                    animate={{ width: `${proj.progress}%` }}
                    className="h-full bg-gradient-to-r from-fuchsia-500 to-violet-500" 
                  />
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </section>

      {/* Upload Modal Mock connected to Backend */}
      <AnimatePresence>
        {isUploading && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
          >
            <motion.div 
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="glass-panel w-full max-w-lg p-8 rounded-3xl relative"
            >
              <button 
                onClick={() => setIsUploading(false)}
                className="absolute top-4 right-6 text-gray-400 hover:text-white"
              >
                ✕
              </button>
              <h2 className="text-2xl font-bold mb-6">Create New Project</h2>
              
              <div className="flex justify-center border-b border-zinc-800 mb-6">
                <button 
                   onClick={() => setUploadMode("url")} 
                   className={`pb-4 px-6 font-semibold flex items-center gap-2 transition-colors ${uploadMode === "url" ? "text-violet-400 border-b-2 border-violet-400" : "text-gray-500 hover:text-gray-300"}`}
                >
                   <LinkIcon className="w-5 h-5" /> Paste URL
                </button>
                <button 
                   onClick={() => setUploadMode("file")}
                   className={`pb-4 px-6 font-semibold flex items-center gap-2 transition-colors ${uploadMode === "file" ? "text-violet-400 border-b-2 border-violet-400" : "text-gray-500 hover:text-gray-300"}`}
                >
                   <FileVideo className="w-5 h-5" /> Upload File
                </button>
              </div>

              <div className="space-y-4">
                {uploadMode === "url" ? (
                  <div>
                    <label className="block text-sm font-medium text-gray-400 mb-2">Paste YouTube URL</label>
                    <input 
                      type="text"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      placeholder="https://youtube.com/watch?v=..."
                      className="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500 transition-all"
                    />
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center">
                    <input 
                      type="file" 
                      accept="video/mp4,video/quicktime,video/x-matroska,video/x-msvideo" 
                      ref={fileInputRef} 
                      onChange={handleFileChange} 
                      className="hidden" 
                    />
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full border-2 border-dashed border-zinc-700 hover:border-violet-500 bg-zinc-900/50 rounded-2xl p-10 flex flex-col items-center justify-center gap-4 transition-colors group cursor-pointer"
                    >
                       <Upload className="w-10 h-10 text-zinc-500 group-hover:text-violet-400 transition-colors" />
                       <span className="text-zinc-300 font-semibold">{selectedFile ? selectedFile.name : "Click here to select a Video File"}</span>
                       {selectedFile && <span className="text-zinc-500 text-sm">{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</span>}
                    </button>
                  </div>
                )}
                
                <button 
                  onClick={handleGenerate}
                  disabled={isSubmitting || (uploadMode === "url" ? !url : !selectedFile)}
                  className={`w-full font-bold py-3 rounded-xl transition-colors mt-4 ${
                    isSubmitting || (uploadMode === "url" ? !url : !selectedFile) 
                      ? "bg-violet-800 text-gray-300 cursor-not-allowed" 
                      : "bg-violet-600 hover:bg-violet-500 text-white neon-glow"
                  }`}
                >
                  {isSubmitting ? "Uploading & Processing..." : "Generate Viral Shorts"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Editor / Clips View Modal */}
      <AnimatePresence>
        {activeProject && (
          <motion.div 
             initial={{ opacity: 0, y: 50 }}
             animate={{ opacity: 1, y: 0 }}
             exit={{ opacity: 0, y: 50 }}
             className="fixed inset-0 z-50 bg-black/95 flex flex-col overflow-y-auto"
          >
            {/* Header */}
            <div className="sticky top-0 z-10 glass-panel px-8 py-4 flex justify-between items-center border-b border-zinc-800">
               <h2 className="text-xl font-bold truncate">{activeProject.title} - Generated Clips</h2>
               <div className="flex gap-4">
                 {activeProject.status === "completed" && (
                   <a 
                     href={`${apiBaseUrl}/api/v1/projects/${activeProject.id}/export-all`}
                     className="px-6 py-2 bg-violet-600 hover:bg-violet-500 rounded-full text-sm font-medium transition flex items-center gap-2"
                   >
                     <Upload className="w-4 h-4 rotate-180" /> Export All (.zip)
                   </a>
                 )}
                 <button 
                   onClick={() => setActiveProject(null)}
                   className="px-6 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-full text-sm font-medium transition"
                 >
                   Close Editor
                 </button>
               </div>
            </div>
            
            {/* Clips Grid */}
            <div className="p-8 lg:p-12 max-w-7xl mx-auto w-full">
               <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                 {Array.from({ length: activeProject.clips || 4 }).map((_, i) => (
                    <motion.div 
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.05 }}
                      key={i} 
                      className="glass-panel overflow-hidden rounded-3xl flex flex-col border border-zinc-800 hover:border-violet-500/50 transition-colors group"
                    >
                      {/* Video Player Placeholder */}
                          <div className="w-full aspect-[9/16] bg-black relative flex items-center justify-center rounded-t-3xl overflow-hidden group">
                        
                        {activeProject.clips_urls && activeProject.clips_urls[i] ? (
                           <ClipVideoPlayer 
                             src={activeProject.clips_urls[i]} 
                             wordsData={activeProject.clips_data ? activeProject.clips_data[i].words : undefined}
                             apiBaseUrl={apiBaseUrl} 
                           />
                        ) : activeProject.sourceUrl && getYouTubeId(activeProject.sourceUrl) ? (
                          <div className="w-[300%] h-full flex items-center justify-center">
                            <iframe 
                              className="w-full h-full object-cover opacity-60 group-hover:opacity-100 transition-opacity duration-500 scale-[2.5]"
                              src={`https://www.youtube.com/embed/${getYouTubeId(activeProject.sourceUrl)}?start=${15 + i * 30}&autoplay=1&mute=1&controls=0&modestbranding=1&loop=1`}
                              allow="autoplay"
                            />
                          </div>
                        ) : (
                          <video 
                            className="w-full h-full object-cover opacity-60 group-hover:opacity-100 transition-opacity duration-500"
                            src="https://www.w3schools.com/html/mov_bbb.mp4"
                            muted
                            loop
                            playsInline
                            onMouseEnter={(e) => e.currentTarget.play()}
                            onMouseLeave={(e) => {
                               e.currentTarget.pause();
                               e.currentTarget.currentTime = 0;
                            }}
                          />
                        )}
                        
                        <div className="absolute top-4 right-4 bg-black/60 px-3 py-1 rounded-full text-xs font-bold border border-emerald-500 text-emerald-400 backdrop-blur-md z-10 pointer-events-none">
                          Score: {activeProject.clips_data ? activeProject.clips_data[i].score : Math.floor(Math.random() * 20 + 80)}
                        </div>
                        
                        {/* Fake captions */}
                        <div className="absolute bottom-16 left-0 right-0 text-center px-4 z-10 pointer-events-none">
                           <span className="bg-yellow-400 text-black font-extrabold text-lg px-3 py-1 leading-relaxed rounded-md transform -skew-x-6 inline-block shadow-lg">
                             VIRAL HOOK {i + 1}
                           </span>
                        </div>
                        
                        {/* Play overlay */}
                        <div className="absolute inset-0 bg-violet-600/0 group-hover:bg-violet-600/10 transition flex items-center justify-center pointer-events-none z-20">
                           <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur opacity-100 group-hover:opacity-0 transition-opacity flex items-center justify-center">
                             <span className="text-white ml-1 font-bold">▶</span>
                           </div>
                        </div>
                      </div>
                      
                      {/* Clip Actions */}
                      <div className="p-5 flex flex-col gap-3 z-10 bg-zinc-950/80">
                         {activeProject.clips_data ? (
                           <>
                             <h4 className="font-bold text-sm tracking-wide leading-tight">{activeProject.clips_data[i].title}</h4>
                             <p className="text-xs text-gray-400 line-clamp-2">{activeProject.clips_data[i].description}</p>
                             <p className="text-xs text-violet-400 font-medium">{activeProject.clips_data[i].hashtags}</p>
                           </>
                         ) : (
                           <>
                             <h4 className="font-bold text-sm tracking-wide">Clip {String(i + 1).padStart(2, '0')}</h4>
                             <p className="text-xs text-gray-400 line-clamp-3">This is the automatically generated transcript chunk that contains the high-conversion narrative hook identified by the AI.</p>
                           </>
                         )}
                         
                         {activeProject.clips_urls && activeProject.clips_urls[i] ? (
                           <a 
                             href={`${apiBaseUrl}/api/v1/projects/download/${activeProject.id}/clip_${i + 1}.mp4`}
                             download={`AIViralShort_Clip_${i + 1}.mp4`}
                             target="_blank"
                             rel="noopener noreferrer"
                             className="w-full mt-2 py-3 bg-zinc-800 hover:bg-violet-600 rounded-xl text-sm font-semibold transition-colors flex items-center justify-center gap-2"
                           >
                             <Upload className="w-4 h-4 rotate-180" /> Export MP4
                           </a>
                         ) : (
                           <button 
                             disabled
                             className="w-full mt-2 py-3 bg-zinc-900 border border-zinc-800 text-gray-500 rounded-xl text-sm font-semibold flex items-center justify-center gap-2"
                           >
                             <Upload className="w-4 h-4 rotate-180" /> Rendering...
                           </button>
                         )}
                      </div>
                    </motion.div>
                 ))}
               </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
