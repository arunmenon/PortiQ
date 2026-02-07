import { Construction } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface ComingSoonProps {
  title: string;
  description?: string;
}

export function ComingSoon({ title, description }: ComingSoonProps) {
  return (
    <div className="flex items-center justify-center py-12">
      <Card className="max-w-md w-full">
        <CardContent className="flex flex-col items-center text-center p-8">
          <Construction className="mb-4 h-12 w-12 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{title}</h2>
          {description && (
            <p className="mt-2 text-sm text-muted-foreground">{description}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
