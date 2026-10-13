import { AppShell, Badge, Button, Card, Group, MantineProvider, PasswordInput, SimpleGrid, Stack, Text, TextInput, Title } from "@mantine/core";
import { FormEvent, useEffect, useRef, useState } from "react";

import "./styles.css";

export function App() {
  const [authenticated, setAuthenticated] = useState(false);
  if (!authenticated) return <MantineProvider defaultColorScheme="dark"><Login onAuthenticated={() => setAuthenticated(true)} /></MantineProvider>;
  return (
    <MantineProvider defaultColorScheme="dark">
      <AppShell header={{ height: 64 }} padding="md" className="investix-shell">
        <AppShell.Header px="md" py="sm" className="topbar">
          <Group justify="space-between">
            <Group gap="xs"><Title order={1} size="h3">Investix</Title><Badge color="cyan" variant="light">Privato</Badge></Group>
            <Button variant="light" size="xs">Aggiorna</Button>
          </Group>
        </AppShell.Header>
        <AppShell.Main>
          <Stack gap="lg" className="dashboard">
            <Group justify="space-between" align="end" className="dashboard-title">
              <div><Text c="dimmed">Portafoglio privato</Text><Title order={2}>Panoramica</Title></div>
              <Text size="sm" c="dimmed">Dati EOD · ultimo aggiornamento: non disponibile</Text>
            </Group>
            <SimpleGrid cols={{ base: 1, xs: 2, md: 4 }} spacing="md">
              <Metric label="Valore portafoglio" value="—" note="Importazione richiesta" />
              <Metric label="P&L totale" value="—" note="Nessuna posizione valorizzata" />
              <Metric label="Rendimento TWR" value="N/D" note="Serie storica non disponibile" />
              <Metric label="Copertura dati" value="Da importare" note="Quotazioni storiche" />
            </SimpleGrid>
            <SimpleGrid cols={{ base: 1, md: 3 }} spacing="md">
              <Card withBorder radius="md" className="chart-card" style={{ gridColumn: "span 2" }}>
                <Group justify="space-between"><Title order={3}>Valore nel tempo</Title><Badge variant="outline">EUR</Badge></Group>
                <PortfolioChart />
                <Text size="xs" c="dimmed">Il grafico usa solo osservazioni persistite; nessun dato live è mostrato come storico.</Text>
              </Card>
              <Card withBorder radius="md"><Title order={3}>Stato dati</Title><Stack mt="md" gap="sm"><Status label="Import STOCKS-26" value="In preparazione" /><Status label="Provider prezzi" value="CSV manuale" /><Status label="Ultima quotazione" value="Non disponibile" /></Stack></Card>
            </SimpleGrid>
              <Card withBorder radius="md" className="positions"><Group justify="space-between"><Title order={3}>Posizioni</Title><Button variant="subtle" size="xs">Registro operazioni</Button></Group><Text c="dimmed" mt="md">Nessuna posizione disponibile: importa prima un export STOCKS-26 validato.</Text></Card>
          </Stack>
        </AppShell.Main>
      </AppShell>
    </MantineProvider>
  );
}

function Login({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    const response = await fetch("http://127.0.0.1:8000/api/auth/login", { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: form.get("username"), password: form.get("password") }) });
    if (response.ok) onAuthenticated(); else setError("Credenziali non valide o API non disponibile");
  }
  return <main className="login"><Card withBorder radius="md" p="xl"><Title order={1}>Investix</Title><Text c="dimmed" mb="lg">Accesso privato</Text><form onSubmit={submit}><Stack><TextInput name="username" label="Utente" required autoComplete="username" /><PasswordInput name="password" label="Password" required autoComplete="current-password" />{error && <Text c="red" size="sm">{error}</Text>}<Button type="submit">Accedi</Button></Stack></form></Card></main>;
}

function Metric({ label, value, note, positive = false }: { label: string; value: string; note: string; positive?: boolean }) {
  return <Card withBorder radius="md"><Text size="sm" c="dimmed">{label}</Text><Text className={positive ? "positive metric" : "metric"}>{value}</Text><Text size="xs" c="dimmed">{note}</Text></Card>;
}

function Status({ label, value }: { label: string; value: string }) {
  return <Group justify="space-between" wrap="nowrap"><Text size="sm">{label}</Text><Text size="sm" c="dimmed">{value}</Text></Group>;
}

function PortfolioChart() {
  const element = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!element.current) return;
    let disposed = false;
    let chart: { setOption: (option: object) => void; resize: () => void; dispose: () => void } | undefined;
    void Promise.all([import("echarts/core"), import("echarts/renderers"), import("echarts/components")]).then(([echarts, renderers, components]) => {
      if (disposed || !element.current) return;
      echarts.use([renderers.SVGRenderer, components.GraphicComponent]);
      chart = echarts.init(element.current, undefined, { renderer: "svg" });
      chart.setOption({
        series: [],
        graphic: { type: "text", left: "center", top: "middle", style: { text: "Nessuna serie storica disponibile", fill: "#9097a6", fontSize: 14 } },
      });
    });
    const resize = () => chart?.resize();
    window.addEventListener("resize", resize);
    return () => { disposed = true; window.removeEventListener("resize", resize); chart?.dispose(); };
  }, []);
  return <div className="chart" ref={element} role="img" aria-label="Grafico del valore del portafoglio: nessuna serie storica disponibile" />;
}
