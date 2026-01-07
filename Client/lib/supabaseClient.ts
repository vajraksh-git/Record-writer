import { createClient } from '@supabase/supabase-js';

// REPLACE these with your actual keys from the Supabase Dashboard -> Settings -> API
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

console.log("Checking Supabase Config:");
console.log("URL:", supabaseUrl);
console.log("Key Length:", supabaseKey ? supabaseKey.length : "UNDEFINED");
console.log("Key Starts With:", supabaseKey ? supabaseKey.substring(0, 10) : "N/A");
// -----------------------------------

export const supabase = createClient(supabaseUrl, supabaseKey);