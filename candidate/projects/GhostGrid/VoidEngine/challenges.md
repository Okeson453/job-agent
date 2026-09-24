# Void Engine — Challenges & Design Notes

**Combined-improvement estimation is explicitly not additive** — the
doc states the net lift is not the arithmetic sum of the four layers'
individual estimated contributions, because module activation is
correlated (e.g. a session with high LSQI quality also tends to have
low SENF entropy). The doc frames this as a compounding, reinforcing
effect rather than four independent edges stacking linearly — worth
being precise about this distinction if the 83-91% figure is ever cited.

**Build-progressivity as risk management:** the explicit design law
that any layer can be disabled and the system degrades to the layer
beneath it is itself the primary defense against Void Engine's own
complexity — each of the 12 Nova Core modules can be verified and
shipped independently rather than as one large all-or-nothing release.
