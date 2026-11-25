import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BadgeIndianRupee,
  Building2,
  MapPin,
  Pencil,
  Phone,
  Plus,
  Tag,
  Trash2,
  Users,
} from "lucide-react";

import { api } from "../lib/api";
import { useBuyers, useOptions } from "../hooks/useReference";
import { formatCurrency, formatDate, formatNumber, isoDaysFromNow, todayIso } from "../lib/utils";
import type { Buyer, BuyerDetail, Offer } from "../types";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog } from "../components/ui/dialog";
import { Field, Input, Select, Textarea } from "../components/ui/input";
import { Alert, DemoBadge, EmptyState, KeyValue, LoadingBlock, PageHeader } from "../components/ui/misc";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableEmpty } from "../components/ui/table";

type BuyerForm = {
  name: string;
  buyer_type: string;
  contact_name: string;
  contact_phone: string;
  market_name: string;
  district: string;
  state: string;
  latitude: string;
  longitude: string;
  notes: string;
};

const emptyBuyer: BuyerForm = {
  name: "",
  buyer_type: "trader",
  contact_name: "",
  contact_phone: "",
  market_name: "",
  district: "",
  state: "",
  latitude: "",
  longitude: "",
  notes: "",
};

type OfferForm = {
  crop: string;
  variety: string;
  offered_price_per_quintal: string;
  min_quantity_quintals: string;
  max_quantity_quintals: string;
  offer_date: string;
  expiry_date: string;
  conditions: string;
  is_active: boolean;
};

function emptyOffer(crop = "Rice"): OfferForm {
  return {
    crop,
    variety: "",
    offered_price_per_quintal: "",
    min_quantity_quintals: "1",
    max_quantity_quintals: "",
    offer_date: todayIso(),
    expiry_date: isoDaysFromNow(30),
    conditions: "",
    is_active: true,
  };
}

function optionalNumber(value: string): number | null {
  return value.trim() === "" ? null : Number(value);
}

function buyerToForm(buyer: Buyer): BuyerForm {
  return {
    name: buyer.name,
    buyer_type: buyer.buyer_type,
    contact_name: buyer.contact_name ?? "",
    contact_phone: buyer.contact_phone ?? "",
    market_name: buyer.market_name ?? "",
    district: buyer.district,
    state: buyer.state,
    latitude: buyer.latitude?.toString() ?? "",
    longitude: buyer.longitude?.toString() ?? "",
    notes: buyer.notes ?? "",
  };
}

export default function BuyersPage() {
  const queryClient = useQueryClient();
  const buyers = useBuyers();
  const options = useOptions();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [buyerDialog, setBuyerDialog] = useState<{ open: boolean; buyer: Buyer | null }>({
    open: false,
    buyer: null,
  });
  const [offerDialog, setOfferDialog] = useState<{ open: boolean; offer: Offer | null }>({
    open: false,
    offer: null,
  });
  const [buyerForm, setBuyerForm] = useState<BuyerForm>(emptyBuyer);
  const [offerForm, setOfferForm] = useState<OfferForm>(emptyOffer());
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const activeId = selectedId ?? buyers.data?.[0]?.id ?? null;

  const detail = useQuery({
    queryKey: ["buyer", activeId],
    queryFn: () => api.get<BuyerDetail>(`/buyers/${activeId}`),
    enabled: activeId !== null,
  });

  const activeBuyer = detail.data ?? buyers.data?.find((row) => row.id === activeId) ?? null;

  const filteredBuyers = useMemo(() => {
    const rows = buyers.data ?? [];
    if (!filter.trim()) return rows;
    const needle = filter.toLowerCase();
    return rows.filter(
      (row) =>
        row.name.toLowerCase().includes(needle) ||
        row.district.toLowerCase().includes(needle) ||
        row.state.toLowerCase().includes(needle),
    );
  }, [buyers.data, filter]);

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["buyers"] });
    void queryClient.invalidateQueries({ queryKey: ["buyer"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard-overview"] });
  }

  const saveBuyer = useMutation({
    mutationFn: () => {
      const payload = {
        name: buyerForm.name.trim(),
        buyer_type: buyerForm.buyer_type,
        contact_name: buyerForm.contact_name.trim() || null,
        contact_phone: buyerForm.contact_phone.trim() || null,
        market_name: buyerForm.market_name.trim() || null,
        district: buyerForm.district.trim(),
        state: buyerForm.state,
        latitude: optionalNumber(buyerForm.latitude),
        longitude: optionalNumber(buyerForm.longitude),
        notes: buyerForm.notes.trim() || null,
      };
      return buyerDialog.buyer
        ? api.patch<Buyer>(`/buyers/${buyerDialog.buyer.id}`, payload)
        : api.post<Buyer>("/buyers", payload);
    },
    onSuccess: (buyer) => {
      setBuyerDialog({ open: false, buyer: null });
      setSelectedId(buyer.id);
      setError(null);
      invalidate();
    },
    onError: (err: Error) => setError(err.message),
  });

  const deleteBuyer = useMutation({
    mutationFn: (id: number) => api.delete(`/buyers/${id}`),
    onSuccess: () => {
      setSelectedId(null);
      invalidate();
    },
    onError: (err: Error) => setError(err.message),
  });

  const saveOffer = useMutation({
    mutationFn: () => {
      if (activeId === null) throw new Error("Select a buyer first");
      const payload = {
        crop: offerForm.crop,
        variety: offerForm.variety.trim() || null,
        offered_price_per_quintal: Number(offerForm.offered_price_per_quintal),
        min_quantity_quintals: Number(offerForm.min_quantity_quintals),
        max_quantity_quintals: optionalNumber(offerForm.max_quantity_quintals),
        offer_date: offerForm.offer_date,
        expiry_date: offerForm.expiry_date,
        conditions: offerForm.conditions.trim() || null,
        is_active: offerForm.is_active,
      };
      return offerDialog.offer
        ? api.patch<Offer>(`/offers/${offerDialog.offer.id}`, payload)
        : api.post<Offer>(`/buyers/${activeId}/offers`, payload);
    },
    onSuccess: () => {
      setOfferDialog({ open: false, offer: null });
      setError(null);
      invalidate();
    },
    onError: (err: Error) => setError(err.message),
  });

  const deleteOffer = useMutation({
    mutationFn: (id: number) => api.delete(`/offers/${id}`),
    onSuccess: invalidate,
    onError: (err: Error) => setError(err.message),
  });

  function openBuyerDialog(buyer: Buyer | null) {
    setError(null);
    setBuyerForm(buyer ? buyerToForm(buyer) : emptyBuyer);
    setBuyerDialog({ open: true, buyer });
  }

  function openOfferDialog(offer: Offer | null) {
    setError(null);
    setOfferForm(
      offer
        ? {
            crop: offer.crop,
            variety: offer.variety ?? "",
            offered_price_per_quintal: offer.offered_price_per_quintal.toString(),
            min_quantity_quintals: offer.min_quantity_quintals.toString(),
            max_quantity_quintals: offer.max_quantity_quintals?.toString() ?? "",
            offer_date: offer.offer_date,
            expiry_date: offer.expiry_date,
            conditions: offer.conditions ?? "",
            is_active: offer.is_active,
          }
        : emptyOffer(),
    );
    setOfferDialog({ open: true, offer });
  }

  if (buyers.isLoading) return <LoadingBlock label="Loading buyers…" />;
  if (buyers.isError) return <Alert variant="error">{(buyers.error as Error).message}</Alert>;

  const offers = detail.data?.offers ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Buyers & offers"
        description="Record private buyers and their price offers. The decision engine compares these with the mandi net realisation."
        actions={
          <Button size="sm" onClick={() => openBuyerDialog(null)}>
            <Plus className="h-4 w-4" /> Add buyer
          </Button>
        }
      />

      {error ? (
        <Alert variant="error" title="Action failed">
          {error}
        </Alert>
      ) : null}

      <Alert variant="info" title="Demo buyer offers are illustrative">
        Seeded buyer offers are labelled <strong>DEMO</strong>. Replace them with your own
        negotiated offers before acting on any decision.
      </Alert>

      {buyers.data!.length === 0 ? (
        <EmptyState
          title="No buyers yet"
          description="Add a local trader, FPO, processor or direct buyer with at least one crop offer."
          icon={<Users className="h-8 w-8" />}
          action={<Button onClick={() => openBuyerDialog(null)}>Add your first buyer</Button>}
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          <div className="space-y-3">
            <Input
              placeholder="Filter by name, district or state…"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            />
            {filteredBuyers.map((buyer) => (
              <button
                key={buyer.id}
                type="button"
                onClick={() => setSelectedId(buyer.id)}
                className={`w-full rounded-lg border p-4 text-left transition-colors ${
                  buyer.id === activeId
                    ? "border-primary bg-primary/5"
                    : "bg-card hover:bg-secondary/40"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="font-medium">{buyer.name}</p>
                  {buyer.is_demo ? <DemoBadge show /> : null}
                </div>
                <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                  <MapPin className="h-3 w-3" />
                  {buyer.district}, {buyer.state}
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant="secondary">{buyer.buyer_type}</Badge>
                  {buyer.market_name ? (
                    <span className="truncate text-xs text-muted-foreground">{buyer.market_name}</span>
                  ) : null}
                </div>
              </button>
            ))}
            {filteredBuyers.length === 0 ? (
              <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                No buyers match “{filter}”.
              </p>
            ) : null}
          </div>

          <div className="space-y-4">
            {activeBuyer ? (
              <>
                <Card>
                  <CardHeader className="flex-row items-start justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-primary" />
                        {activeBuyer.name} {activeBuyer.is_demo ? <DemoBadge show /> : null}
                      </CardTitle>
                      <CardDescription>
                        {activeBuyer.district}, {activeBuyer.state}
                      </CardDescription>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button variant="outline" size="sm" onClick={() => openBuyerDialog(activeBuyer)}>
                        <Pencil className="h-3.5 w-3.5" /> Edit
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => {
                          if (window.confirm(`Delete ${activeBuyer.name} and all offers?`)) {
                            deleteBuyer.mutate(activeBuyer.id);
                          }
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5" /> Delete
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      <div className="rounded-lg bg-secondary/50 p-3">
                        <p className="text-xs uppercase text-muted-foreground">Type</p>
                        <p className="mt-1 text-sm font-medium">{activeBuyer.buyer_type}</p>
                      </div>
                      <div className="rounded-lg bg-secondary/50 p-3">
                        <p className="flex items-center gap-1 text-xs uppercase text-muted-foreground">
                          <Phone className="h-3 w-3" /> Contact
                        </p>
                        <p className="mt-1 text-sm font-medium">
                          {activeBuyer.contact_name ?? "—"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {activeBuyer.contact_phone ?? "No phone"}
                        </p>
                      </div>
                      <div className="rounded-lg bg-secondary/50 p-3">
                        <p className="text-xs uppercase text-muted-foreground">Market</p>
                        <p className="mt-1 text-sm font-medium">
                          {activeBuyer.market_name ?? "—"}
                        </p>
                      </div>
                      <div className="rounded-lg bg-secondary/50 p-3">
                        <p className="text-xs uppercase text-muted-foreground">Coordinates</p>
                        <p className="mt-1 text-sm font-medium">
                          {activeBuyer.latitude !== null
                            ? `${activeBuyer.latitude}, ${activeBuyer.longitude}`
                            : "Not set"}
                        </p>
                      </div>
                    </div>
                    {activeBuyer.notes ? (
                      <p className="mt-3 text-sm text-muted-foreground">{activeBuyer.notes}</p>
                    ) : null}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex-row items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <Tag className="h-4 w-4 text-primary" /> Price offers
                      </CardTitle>
                      <CardDescription>
                        Only active, unexpired offers inside the quantity band are eligible.
                      </CardDescription>
                    </div>
                    <Button size="sm" onClick={() => openOfferDialog(null)}>
                      <Plus className="h-4 w-4" /> Add offer
                    </Button>
                  </CardHeader>
                  <CardContent className="p-0">
                    {detail.isLoading ? (
                      <LoadingBlock />
                    ) : (
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Crop</TableHead>
                            <TableHead className="text-right">Price</TableHead>
                            <TableHead className="text-right">Quantity band</TableHead>
                            <TableHead>Offer date</TableHead>
                            <TableHead>Expiry</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead className="text-right">Actions</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {offers.length > 0 ? (
                            offers.map((offer) => {
                              const expired = offer.expiry_date < todayIso();
                              return (
                                <TableRow key={offer.id}>
                                  <TableCell>
                                    <p className="font-medium">{offer.crop}</p>
                                    <p className="text-xs text-muted-foreground">
                                      {offer.variety ?? "—"}
                                    </p>
                                  </TableCell>
                                  <TableCell className="text-right font-medium">
                                    {formatCurrency(offer.offered_price_per_quintal, 0)}
                                  </TableCell>
                                  <TableCell className="text-right text-xs">
                                    {formatNumber(offer.min_quantity_quintals, 0)}
                                    {offer.max_quantity_quintals !== null
                                      ? `–${formatNumber(offer.max_quantity_quintals, 0)}`
                                      : "+"}{" "}
                                    q
                                  </TableCell>
                                  <TableCell>{formatDate(offer.offer_date)}</TableCell>
                                  <TableCell>{formatDate(offer.expiry_date)}</TableCell>
                                  <TableCell>
                                    {!offer.is_active ? (
                                      <Badge variant="secondary">inactive</Badge>
                                    ) : expired ? (
                                      <Badge variant="danger">expired</Badge>
                                    ) : (
                                      <Badge variant="success">active</Badge>
                                    )}
                                    {offer.is_demo ? <DemoBadge show /> : null}
                                  </TableCell>
                                  <TableCell>
                                    <div className="flex justify-end gap-1">
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        aria-label="Edit offer"
                                        onClick={() => openOfferDialog(offer)}
                                      >
                                        <Pencil className="h-4 w-4" />
                                      </Button>
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        aria-label="Delete offer"
                                        onClick={() => {
                                          if (window.confirm("Delete this offer?")) {
                                            deleteOffer.mutate(offer.id);
                                          }
                                        }}
                                      >
                                        <Trash2 className="h-4 w-4 text-destructive" />
                                      </Button>
                                    </div>
                                  </TableCell>
                                </TableRow>
                              );
                            })
                          ) : (
                            <TableEmpty colSpan={7} message="No offers recorded for this buyer." />
                          )}
                        </TableBody>
                      </Table>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BadgeIndianRupee className="h-4 w-4 text-primary" /> Offer summary
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {offers.length > 0 ? (
                      <div className="grid gap-3 sm:grid-cols-3">
                        <KeyValue
                          label="Offers"
                          value={String(offers.length)}
                        />
                        <KeyValue
                          label="Best price"
                          value={formatCurrency(
                            Math.max(...offers.map((row) => row.offered_price_per_quintal)),
                            0,
                          )}
                        />
                        <KeyValue
                          label="Active offers"
                          value={String(
                            offers.filter((row) => row.is_active && row.expiry_date >= todayIso())
                              .length,
                          )}
                        />
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No offers yet.</p>
                    )}
                  </CardContent>
                </Card>
              </>
            ) : null}
          </div>
        </div>
      )}

      <Dialog
        open={buyerDialog.open}
        onClose={() => setBuyerDialog({ open: false, buyer: null })}
        title={buyerDialog.buyer ? "Edit buyer" : "Add buyer"}
        description="Buyer location is used to estimate road distance and transport cost."
        footer={
          <>
            <Button variant="outline" onClick={() => setBuyerDialog({ open: false, buyer: null })}>
              Cancel
            </Button>
            <Button
              onClick={() => saveBuyer.mutate()}
              loading={saveBuyer.isPending}
              disabled={!buyerForm.name || !buyerForm.district || !buyerForm.state}
            >
              {buyerDialog.buyer ? "Save changes" : "Create buyer"}
            </Button>
          </>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Buyer name" className="sm:col-span-2">
            <Input
              value={buyerForm.name}
              onChange={(event) => setBuyerForm({ ...buyerForm, name: event.target.value })}
              placeholder="Nashik FPO"
            />
          </Field>
          <Field label="Buyer type">
            <Select
              value={buyerForm.buyer_type}
              onChange={(event) => setBuyerForm({ ...buyerForm, buyer_type: event.target.value })}
            >
              {(options.data?.buyer_types ?? []).map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Market / mandi">
            <Input
              value={buyerForm.market_name}
              onChange={(event) => setBuyerForm({ ...buyerForm, market_name: event.target.value })}
            />
          </Field>
          <Field label="Contact name">
            <Input
              value={buyerForm.contact_name}
              onChange={(event) => setBuyerForm({ ...buyerForm, contact_name: event.target.value })}
            />
          </Field>
          <Field label="Contact phone">
            <Input
              value={buyerForm.contact_phone}
              onChange={(event) => setBuyerForm({ ...buyerForm, contact_phone: event.target.value })}
            />
          </Field>
          <Field label="District">
            <Input
              value={buyerForm.district}
              onChange={(event) => setBuyerForm({ ...buyerForm, district: event.target.value })}
            />
          </Field>
          <Field label="State">
            <Select
              value={buyerForm.state}
              onChange={(event) => setBuyerForm({ ...buyerForm, state: event.target.value })}
            >
              <option value="">Select state</option>
              {(options.data?.states ?? []).map((state) => (
                <option key={state} value={state}>
                  {state}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Latitude (optional)">
            <Input
              type="number"
              step="any"
              value={buyerForm.latitude}
              onChange={(event) => setBuyerForm({ ...buyerForm, latitude: event.target.value })}
            />
          </Field>
          <Field label="Longitude (optional)">
            <Input
              type="number"
              step="any"
              value={buyerForm.longitude}
              onChange={(event) => setBuyerForm({ ...buyerForm, longitude: event.target.value })}
            />
          </Field>
          <Field label="Notes" className="sm:col-span-2">
            <Textarea
              value={buyerForm.notes}
              onChange={(event) => setBuyerForm({ ...buyerForm, notes: event.target.value })}
            />
          </Field>
        </div>
      </Dialog>

      <Dialog
        open={offerDialog.open}
        onClose={() => setOfferDialog({ open: false, offer: null })}
        title={offerDialog.offer ? "Edit offer" : "Add price offer"}
        description="Offers are private to your account and are compared with mandi prices."
        footer={
          <>
            <Button variant="outline" onClick={() => setOfferDialog({ open: false, offer: null })}>
              Cancel
            </Button>
            <Button
              onClick={() => saveOffer.mutate()}
              loading={saveOffer.isPending}
              disabled={!offerForm.offered_price_per_quintal || !offerForm.crop}
            >
              {offerDialog.offer ? "Save changes" : "Create offer"}
            </Button>
          </>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Crop">
            <Select
              value={offerForm.crop}
              onChange={(event) => setOfferForm({ ...offerForm, crop: event.target.value })}
            >
              {(options.data?.crops ?? []).map((crop) => (
                <option key={crop} value={crop}>
                  {crop}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Variety">
            <Input
              value={offerForm.variety}
              onChange={(event) => setOfferForm({ ...offerForm, variety: event.target.value })}
            />
          </Field>
          <Field label="Price (INR/quintal)">
            <Input
              type="number"
              min="1"
              step="0.01"
              value={offerForm.offered_price_per_quintal}
              onChange={(event) =>
                setOfferForm({ ...offerForm, offered_price_per_quintal: event.target.value })
              }
            />
          </Field>
          <Field label="Minimum quantity (q)">
            <Input
              type="number"
              min="0.01"
              step="0.01"
              value={offerForm.min_quantity_quintals}
              onChange={(event) =>
                setOfferForm({ ...offerForm, min_quantity_quintals: event.target.value })
              }
            />
          </Field>
          <Field label="Maximum quantity (q, optional)">
            <Input
              type="number"
              min="0.01"
              step="0.01"
              value={offerForm.max_quantity_quintals}
              onChange={(event) =>
                setOfferForm({ ...offerForm, max_quantity_quintals: event.target.value })
              }
            />
          </Field>
          <Field label="Active">
            <Select
              value={offerForm.is_active ? "yes" : "no"}
              onChange={(event) =>
                setOfferForm({ ...offerForm, is_active: event.target.value === "yes" })
              }
            >
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </Select>
          </Field>
          <Field label="Offer date">
            <Input
              type="date"
              value={offerForm.offer_date}
              onChange={(event) => setOfferForm({ ...offerForm, offer_date: event.target.value })}
            />
          </Field>
          <Field label="Expiry date">
            <Input
              type="date"
              value={offerForm.expiry_date}
              onChange={(event) => setOfferForm({ ...offerForm, expiry_date: event.target.value })}
            />
          </Field>
          <Field label="Conditions" className="sm:col-span-2">
            <Textarea
              value={offerForm.conditions}
              onChange={(event) => setOfferForm({ ...offerForm, conditions: event.target.value })}
              placeholder="Moisture limit, grading, payment terms…"
            />
          </Field>
        </div>
      </Dialog>
    </div>
  );
}
