# Vorschlag 0001: Namenskonflikt mit eingebauten Connectoren melden

**Status: Vorschlag, nicht angewendet.** Der Host bleibt unverändert, bis der Maintainer entscheidet.

## Problem

`load_manifest` prüft eingebaute Namen zuerst. Ein installiertes Paket, das `sqlserver` anbietet,
wird ohne Meldung ignoriert: Der Nutzer glaubt, sein Paket laufe, und bekommt den eingebauten Adapter
oder den Hinweis auf ein Extra. Das verletzt die Regel „kein stilles Überschreiben“. Außerdem
empfiehlt der Host auch externen Paketen `pip install tarel[extra]`.

## Änderung

Siehe [0001-connector-name-collision.patch](0001-connector-name-collision.patch):

- Ein Entry Point mit eingebautem Namen ergibt `ambiguous_connector`, statt ignoriert zu werden.
- Der Installationshinweis unterscheidet eingebaute und externe Connectoren.

Für vorhandene Nutzer ändert sich nichts, solange kein solches Paket installiert ist.

## Vertragstest

`contract-tests/test_host_loading.py::test_known_gap_a_plugin_named_like_a_builtin_is_silently_ignored`
hält das heutige Verhalten fest. Mit dem Patch schlägt er absichtlich fehl und wird dann durch die
Erwartung `ambiguous_connector` ersetzt. Geprüft auf einer Wegwerf-Kopie von `eeb559f`, siehe
`IMPLEMENTATION_STATUS.md`.

## Offene Entscheidung

Soll SQL Server später aus dem Host in ein externes Paket umziehen? Das wäre eine zweite, größere
Entscheidung mit Übergang für heutige Nutzer von `tarel[sqlserver]`.
