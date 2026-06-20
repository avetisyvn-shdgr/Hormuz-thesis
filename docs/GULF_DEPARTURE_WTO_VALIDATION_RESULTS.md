# Gulf departure validation against WTO/AXSMarine

**Status:** Verified locally without rescaling or calibration.  
**Purpose:** Independent validation of the GFW-inferred Gulf LNG departure
signal, not validation of actual cargo quantity or sailed distance.

## Locked comparison

- Equal 94-day windows: 28 February through 1 June in 2025 and 2026.
- GFW terminal radius: 30 km.
- Inside-Hormuz liquefaction origins: QatarEnergy LNG North and Das Island LNG.
- Oman Qalhat is excluded because it lies outside the Strait of Hormuz.
- GFW departure date is the UTC end date of the classified terminal visit.
- The WTO measure is its published daily LNG outbound shipment-volume index;
  it is not converted into tonnes, vessel counts, or nominal capacity.

## Result

| Measure | Pre | Post | Change |
|---|---:|---:|---:|
| GFW inferred Gulf departure calls | 171 | 12 | -93.0% |
| GFW nominal departure capacity | 25.52m m3 | 1.84m m3 | -92.8% |
| WTO mean outbound LNG index | 101.78 | 1.38 | -98.6% |
| GFW active departure days | 79 | 10 | descriptive |
| WTO nonzero index days | 92 | 4 | descriptive |

The two independent sources strongly agree on the direction and approximate
magnitude of the collapse. They do not match exactly, and no scaling factor was
estimated to make them agree.

## Timing agreement

For nominal GFW departure capacity versus the WTO index:

| Window | Daily Pearson | Daily Spearman | Complete-week Pearson | Complete-week Spearman |
|---|---:|---:|---:|---:|
| Pre | 0.43 | 0.42 | 0.46 | 0.60 |
| Post | 0.20 | 0.27 | 0.41 | 0.32 |

The pre-period timing relationship is moderate. Post-period correlation is weak
daily and moderate in complete seven-day bins, partly because both series are
mostly zero and only 12 GFW calls remain. All pre-specified daily lags from -3
to +3 days are retained in the correlation output; zero lag remains primary.

## Defensible conclusion

The WTO/AXSMarine series independently corroborates the severe post-disruption
collapse in the inferred Qatar/UAE LNG departure signal. It provides weaker
support for exact daily event alignment. This validation strengthens the
coverage interpretation of the GFW reconstruction but does not establish laden
state, actual shipment volume, ton-miles, freight rates, or a causal ATT.
