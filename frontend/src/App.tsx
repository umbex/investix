import { AppShell, MantineProvider, Text, Title } from "@mantine/core";

export function App() {
  return (
    <MantineProvider defaultColorScheme="dark">
      <AppShell header={{ height: 64 }} padding="md">
        <AppShell.Header px="md" py="sm">
          <Title order={1} size="h3">Investix</Title>
        </AppShell.Header>
        <AppShell.Main>
          <Text c="dimmed">Portafoglio privato</Text>
        </AppShell.Main>
      </AppShell>
    </MantineProvider>
  );
}
