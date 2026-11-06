# Vorschlag 0002: Connectoren dürfen sagen, wie vollständig sie sehen

**Status: zur Besprechung. Dies ist ein neuer Kernvertrag, also nichts festgelegt.**

## Problem

`CatalogResult` kennt nur Objekte. Oracles `ALL_*`-Sichten zeigen ein Objekt nach einem entzogenen
Recht einfach nicht mehr. Der Connector kann das nicht von einer Löschung unterscheiden, also
berichtet der Host `object_removed`:

```text
Recht entzogen -> Objekt fehlt in ALL_TABLES -> graph refresh meldet object_removed
              -> sync veröffentlicht "complete" -> Zentrale meldet source_deleted
```

Das widerspricht direkt der Regel: fehlende Objekte nicht als belegte Löschung melden. Der Test
`test_known_gap_a_revoked_grant_looks_like_a_deletion` hält das fest. SQL Server dürfte ähnlich
betroffen sein, das ist aber nicht geprüft.

## Vorschlag zum Besprechen

Ein optionales Feld, abwärtskompatibel mit dem Standardwert „unbekannt“:

```python
@dataclass(frozen=True, slots=True)
class CatalogResult:
    ...
    visibility: str = "unknown"  # "complete" | "account_limited" | "unknown"
```

Der Host hält den Wert in `observation.json` fest. Bei `account_limited` markiert ein Refresh
verschwundene Objekte als `no_longer_visible` statt als entfernt, und `sync publish` setzt den Grund
nicht auf `source_deleted`.

## Fragen an den Maintainer

1. Reicht dieses eine Feld, oder braucht es eine Liste nicht lesbarer Schemas?
2. Wird ein nicht mehr sichtbares Objekt im Graphen behalten oder entfernt und nur anders begründet?
3. Wie weit soll das in den Sync-Vertrag reichen, der gerade erst stabil geworden ist?
