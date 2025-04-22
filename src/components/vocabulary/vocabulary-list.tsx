"use client";

import { useState, useEffect } from "react";
import { createSupabaseClient } from "@/lib/supabase/client";
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";

type Vocabulary = {
  id: string;
  word: string;
  language: string;
  entry_id: string;
  created_at: string;
};

const languageOptions = [
  { value: "all", label: "All Languages" },
  { value: "spanish", label: "Spanish" },
  { value: "french", label: "French" },
  { value: "german", label: "German" },
  { value: "italian", label: "Italian" },
  { value: "portuguese", label: "Portuguese" },
  { value: "chinese", label: "Chinese" },
  { value: "japanese", label: "Japanese" },
  { value: "korean", label: "Korean" },
  { value: "russian", label: "Russian" },
  { value: "arabic", label: "Arabic" },
];

export function VocabularyList() {
  const [vocabulary, setVocabulary] = useState<Vocabulary[]>([]);
  const [loading, setLoading] = useState(true);
  const [language, setLanguage] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  const supabase = createSupabaseClient();

  useEffect(() => {
    async function fetchVocabulary() {
      try {
        const { data: user } = await supabase.auth.getUser();
        
        if (!user.user) {
          return;
        }

        let query = supabase
          .from("vocabulary")
          .select("*")
          .order("created_at", { ascending: false });
        
        if (language !== "all") {
          query = query.eq("language", language);
        }

        const { data, error } = await query;

        if (error) {
          throw error;
        }

        setVocabulary(data || []);
      } catch (error) {
        console.error("Error fetching vocabulary:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchVocabulary();
  }, [language]);

  const filteredVocabulary = vocabulary.filter(item => 
    item.word.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div>
        <div className="flex items-center space-x-4 mb-6">
          <Skeleton className="h-10 w-[180px]" />
          <Skeleton className="h-10 w-full" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 9 }).map((_, i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-5 w-1/2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-1/3 mb-2" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (vocabulary.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center">
        <h3 className="text-lg font-medium">No vocabulary words yet</h3>
        <p className="text-sm text-muted-foreground">
          Start writing journal entries to build your vocabulary.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row items-start sm:items-center space-y-4 sm:space-y-0 space-x-0 sm:space-x-4 mb-6">
        <Select 
          value={language} 
          onValueChange={setLanguage}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by language" />
          </SelectTrigger>
          <SelectContent>
            {languageOptions.map(option => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        
        <Input
          placeholder="Search vocabulary..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full"
        />
      </div>
      
      {filteredVocabulary.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center">
          <h3 className="text-lg font-medium">No matching words</h3>
          <p className="text-sm text-muted-foreground">
            Try a different search term or language filter.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredVocabulary.map((item) => (
            <Card key={item.id}>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">{item.word}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground capitalize">
                  {item.language}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}