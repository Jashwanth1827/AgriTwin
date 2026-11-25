import { useQuery } from "@tanstack/react-query";

import { api } from "../lib/api";
import type { Buyer, Crop, Farm, SystemOptions } from "../types";

export function useOptions() {
  return useQuery({
    queryKey: ["system-options"],
    queryFn: () => api.get<SystemOptions>("/system/options"),
    staleTime: 10 * 60_000,
  });
}

export function useFarms() {
  return useQuery({
    queryKey: ["farms"],
    queryFn: () => api.get<Farm[]>("/farms"),
  });
}

export function useCrops(farmId?: number) {
  return useQuery({
    queryKey: ["crops", farmId ?? "all"],
    queryFn: () => api.get<Crop[]>(farmId ? `/farms/${farmId}/crops` : "/crops"),
  });
}

export function useBuyers() {
  return useQuery({
    queryKey: ["buyers"],
    queryFn: () => api.get<Buyer[]>("/buyers"),
  });
}
