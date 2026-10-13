import { AppShell, Badge, Button, Card, Group, MantineProvider, SimpleGrid, Stack, Table, Text, Title } from "@mantine/core";

import "./styles.css";

const positions = [
  ["VWCE", "42,00", "€ 5.904", "+€ 684", "33%"],
  ["AAPL", "12,00", "€ 2.214", "+€ 305", "12%"],
  ["EQQQ", "18,00", "€ 1.896", "+€ 196", "11%"],
];

export function App() {
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
              <Metric label="Valore portafoglio" value="€ 17.842" note="Valore stimato" />
              <Metric label="P&L totale" value="+€ 1.842" note="Include realizzato" positive />
              <Metric label="Rendimento TWR" value="+12,4%" note="Periodo disponibile" positive />
              <Metric label="Copertura dati" value="Da importare" note="Quotazioni storiche" />
            </SimpleGrid>
            <SimpleGrid cols={{ base: 1, md: 3 }} spacing="md">
              <Card withBorder radius="md" className="chart-card" style={{ gridColumn: "span 2" }}>
                <Group justify="space-between"><Title order={3}>Valore nel tempo</Title><Badge variant="outline">EUR</Badge></Group>
                <div className="chart" role="img" aria-label="Grafico del valore del portafoglio, in attesa di dati importati"><svg viewBox="0 0 600 180" preserveAspectRatio="none"><polyline points="0,150 80,130 150,142 235,95 330,108 410,66 500,78 600,30" /></svg></div>
                <Text size="xs" c="dimmed">Il grafico usa solo osservazioni persistite; nessun dato live è mostrato come storico.</Text>
              </Card>
              <Card withBorder radius="md"><Title order={3}>Stato dati</Title><Stack mt="md" gap="sm"><Status label="Import STOCKS-26" value="In preparazione" /><Status label="Provider prezzi" value="CSV manuale" /><Status label="Ultima quotazione" value="Non disponibile" /></Stack></Card>
            </SimpleGrid>
            <Card withBorder radius="md" className="positions"><Group justify="space-between"><Title order={3}>Posizioni</Title><Button variant="subtle" size="xs">Registro operazioni</Button></Group><Table.ScrollContainer minWidth={540}><Table striped highlightOnHover mt="md"><Table.Thead><Table.Tr><Table.Th>Ticker</Table.Th><Table.Th>Quantità</Table.Th><Table.Th>Valore EUR</Table.Th><Table.Th>P&L aperto</Table.Th><Table.Th>Peso</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{positions.map((row) => <Table.Tr key={row[0]}>{row.map((cell) => <Table.Td key={cell}>{cell}</Table.Td>)}</Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer></Card>
          </Stack>
        </AppShell.Main>
      </AppShell>
    </MantineProvider>
  );
}

function Metric({ label, value, note, positive = false }: { label: string; value: string; note: string; positive?: boolean }) {
  return <Card withBorder radius="md"><Text size="sm" c="dimmed">{label}</Text><Text className={positive ? "positive metric" : "metric"}>{value}</Text><Text size="xs" c="dimmed">{note}</Text></Card>;
}

function Status({ label, value }: { label: string; value: string }) {
  return <Group justify="space-between" wrap="nowrap"><Text size="sm">{label}</Text><Text size="sm" c="dimmed">{value}</Text></Group>;
}
