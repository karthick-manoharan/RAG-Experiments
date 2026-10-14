import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-16">
      <section className="w-full max-w-lg space-y-6">
        <p className="text-sm font-medium tracking-wide text-muted-foreground">
          Foundation
        </p>
        <h1 className="text-5xl font-semibold tracking-tight">PaperChat</h1>
        <p className="text-lg leading-relaxed text-muted-foreground">
          A foundation for exploring research papers. The application shell is
          ready; paper ingestion and conversations are coming later.
        </p>
        <Button type="button">UI configured</Button>
      </section>
    </main>
  );
}
