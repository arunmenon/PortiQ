"use client";

import { useQuery } from "@tanstack/react-query";
import {
  getCombinedIntelligence,
  type IntelligenceResponse,
  type IntelligenceParams,
} from "@/lib/api/intelligence";
import { useDebounce } from "./use-debounce";

interface UseIntelligenceOptions {
  deliveryPort?: string;
  impaCodes?: string[];
  vesselId?: string;
  deliveryDate?: string;
  biddingDeadline?: string;
}

export function useIntelligence({
  deliveryPort,
  impaCodes,
  vesselId,
  deliveryDate,
  biddingDeadline,
}: UseIntelligenceOptions) {
  const debouncedPort = useDebounce(deliveryPort, 500);
  const debouncedImpaCodes = useDebounce(impaCodes, 500);

  const hasPort = !!debouncedPort && debouncedPort.trim().length > 0;
  const impaCodesParam = debouncedImpaCodes?.length
    ? debouncedImpaCodes.join(",")
    : undefined;

  return useQuery<IntelligenceResponse>({
    queryKey: [
      "intelligence",
      debouncedPort,
      impaCodesParam,
      vesselId,
      deliveryDate,
      biddingDeadline,
    ],
    queryFn: () => {
      const params: IntelligenceParams = {
        delivery_port: debouncedPort,
        impa_codes: impaCodesParam,
        vessel_id: vesselId,
        delivery_date: deliveryDate,
        bidding_deadline: biddingDeadline,
      };
      return getCombinedIntelligence(params);
    },
    enabled: hasPort,
    staleTime: 30_000,
    retry: 1,
  });
}
