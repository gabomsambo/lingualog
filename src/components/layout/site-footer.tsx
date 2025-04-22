export function SiteFooter() {
    return (
      <footer className="border-t py-6 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-16 md:flex-row">
          <p className="text-center text-sm leading-loose text-muted-foreground md:text-left">
            Built with Next.js, Supabase, and AI-powered language tools.
          </p>
          <p className="text-center text-sm leading-loose text-muted-foreground md:text-left">
            LinguaLog © {new Date().getFullYear()}
          </p>
        </div>
      </footer>
    );
  }