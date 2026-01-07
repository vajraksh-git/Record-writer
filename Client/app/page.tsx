'use client';
import { useState } from 'react';
import Image from 'next/image';
import { supabase } from '@/lib/supabaseClient'; // Make sure this path is correct!

// --- 1. CHILD COMPONENT: Paper Selector ---
// Now accepts 'value' and 'onChange' from the parent
const PaperSelector = ({ value, onChange }: { value: string, onChange: (val: string) => void }) => {
  const sizes = [
    { label: 'A4 (Standard)', value: 'A4' },
    { label: 'A3 (Large)', value: 'A3' },
    { label: 'Letter (US)', value: 'Letter' }
  ];

  return (
    <div className="flex flex-col gap-2 p-4 border rounded shadow-sm w-full bg-white">
      <label className="text-gray-700 font-bold">Choose Paper Size</label>
      <select 
        value={value} 
        onChange={(e) => onChange(e.target.value)}
        className="text-black p-2 border rounded-md bg-white shadow-sm focus:ring-2 ring-blue-500"
      >
        <option value="" disabled>-- Select a size --</option>
        {sizes.map((size) => (
          <option key={size.value} value={size.value}>
            {size.label}
          </option>
        ))}
      </select>
    </div>
  );
};

// --- 2. CHILD COMPONENT: File Uploader ---
// Now sends the file UP to the parent via 'onFileSelect'
const FileUploader = ({ onFileSelect }: { onFileSelect: (file: File | null) => void }) => {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null); // Preview can stay local

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    // Validation
    const validTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/webp'];
    if (!validTypes.includes(selectedFile.type)) {
      alert("Only PDF, JPG, and PNG files are allowed.");
      return;
    }

    // SEND TO PARENT
    onFileSelect(selectedFile);

    // Local Preview Logic
    if (selectedFile.type.startsWith('image/')) {
      setPreviewUrl(URL.createObjectURL(selectedFile));
    } else {
      setPreviewUrl(null);
    }
  };

  return (
    <div className="flex flex-col gap-3 p-4 border rounded shadow-sm w-full mt-4 bg-white">
      <label className="text-gray-700 font-bold">Upload Lab Record</label>
      <input 
        type="file" 
        accept=".pdf, image/*" 
        onChange={handleFileChange}
        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
      />
      {previewUrl && (
        <div className="relative w-full h-40 mt-2 border rounded overflow-hidden">
          <Image src={previewUrl} alt="Preview" fill className="object-contain" />
        </div>
      )}
    </div>
  );
};

// --- 3. CHILD COMPONENT: Prompt Input ---
// Now accepts 'value' and 'onChange' from parent
const PromptInput = ({ value, onChange }: { value: string, onChange: (val: string) => void }) => {
  return (
    <div className="flex flex-col gap-2 p-4 border rounded shadow-sm w-full mt-4 bg-white">
      <label className="text-gray-700 font-bold">Additional Instructions</label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="E.g., Skip the diagrams, remove values in Table 2..."
        rows={4}
        className="w-full p-2 text-black border rounded-md bg-white shadow-sm focus:ring-2 ring-blue-500 resize-none"
      />
      <p className="text-xs text-gray-400 text-right">{value.length} characters</p>
    </div>
  );
};

// --- 4. MAIN PARENT COMPONENT ---
export default function Home() {
  // STATE IS NOW HERE (At the top level)
  const [file, setFile] = useState<File | null>(null);
  const [paperSize, setPaperSize] = useState('');
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // LOGIC IS NOW HERE (Where it can see the state)
  const handleSubmit = async () => {
    if (!file || !paperSize) return alert("Missing fields");
    setIsLoading(true);

    try {
      // 1. Upload File
      const fileName = `${Date.now()}_${file.name}`;
      const { error: uploadError } = await supabase.storage
        .from('uploads')
        .upload(fileName, file);

      if (uploadError) throw uploadError;

      // 2. Get URL
      const { data: { publicUrl } } = supabase.storage
        .from('uploads')
        .getPublicUrl(fileName);

      // 3. Save Job to DB
      const { error: dbError } = await supabase
        .from('jobs')
        .insert([{ 
          status: 'pending', 
          paper_size: paperSize, 
          custom_prompt: prompt, 
          file_url: publicUrl 
        }]);

      if (dbError) throw dbError;

      alert("Success! Job Submitted.");
      
      // Optional: Reset form
      setFile(null);
      setPrompt('');

    } catch (error: any) {
      console.error('Error:', error);
      alert("Error: " + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gray-50 py-10">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Record Writer Setup</h1>
      
      <div className="flex flex-col gap-4 w-full max-w-sm">
        
        {/* Pass the "Remote Controls" down to the children */}
        <FileUploader onFileSelect={setFile} />
        
        <PaperSelector value={paperSize} onChange={setPaperSize} />
        
        <PromptInput value={prompt} onChange={setPrompt} />
        
        <button 
          onClick={handleSubmit}
          disabled={isLoading}
          className={`mt-4 text-white font-semibold py-3 rounded-lg shadow transition-colors ${isLoading ? 'bg-gray-400' : 'bg-blue-600 hover:bg-blue-700'}`}
        >
          {isLoading ? "Uploading..." : "Generate Record"}
        </button>
      </div>
    </main>
  );
}