/**
 * Network Topology Report
 * Visualizes network circuits, connectivity, and infrastructure topology
 */

import { useEffect, useState, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Paper,
  Chip,
  Typography,
  Grid,
  TableContainer,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
} from '@mui/material';
import { api } from '@/api/client';
import ReportShell from '../ReportShell';

interface NetworkCircuit {
  id: string;
  name: string;
  subtype?: string;
  attributes?: Record<string, any>;
  description?: string;
}

export default function NetworkTopologyReport() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [circuits, setCircuits] = useState<NetworkCircuit[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const resp = await api.get<{ items: NetworkCircuit[] }>(
          '/cards?type=NetworkCircuit&page_size=200'
        );
        setCircuits(resp.items || []);
        setLoading(false);
      } catch (err: any) {
        setError(err.detail || 'Failed to load network circuits');
        setLoading(false);
      }
    })();
  }, []);

  const topology = useMemo(() => {
    const byType: Record<string, number> = {};
    let totalBandwidth = 0;

    circuits.forEach((c) => {
      const type = c.subtype || 'unknown';
      byType[type] = (byType[type] || 0) + 1;
      // Parse bandwidth if available
      const bw = c.attributes?.bandwidth;
      if (bw && typeof bw === 'string') {
        const match = bw.match(/(\d+)/);
        if (match) totalBandwidth += parseInt(match[1], 10);
      }
    });

    return {
      totalCircuits: circuits.length,
      byType,
      averageBandwidth: totalBandwidth > 0 ? `${Math.round(totalBandwidth / circuits.length)} Mbps` : 'N/A',
    };
  }, [circuits]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  const CIRCUIT_COLORS: Record<string, string> = {
    leased: '#ff9800',
    internet: '#2196f3',
    mpls: '#4caf50',
    unknown: '#9e9e9e',
  };

  return (
    <ReportShell title="Network Topology" icon="lan" hasTableToggle={false}>
      {/* Summary stats */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="primary">
              {topology.totalCircuits}
            </Typography>
            <Typography variant="caption">Total Circuits</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="success.main">
              {topology.byType['mpls'] || 0}
            </Typography>
            <Typography variant="caption">MPLS</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="info.main">
              {topology.byType['internet'] || 0}
            </Typography>
            <Typography variant="caption">Internet</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="warning.main">
              {topology.byType['leased'] || 0}
            </Typography>
            <Typography variant="caption">Leased Lines</Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Circuit type breakdown */}
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Circuit Types Breakdown
      </Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        {Object.entries(topology.byType).map(([type, count]) => (
          <Grid item xs={12} sm={6} md={4} key={type}>
            <Card>
              <CardContent sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    {type === 'unknown' ? 'Unknown' : type.charAt(0).toUpperCase() + type.slice(1)}
                  </Typography>
                  <Chip
                    label={`${count}`}
                    sx={{
                      backgroundColor: CIRCUIT_COLORS[type],
                      color: 'white',
                      fontWeight: 600,
                    }}
                  />
                </Box>

                {/* Progress bar */}
                <Box
                  sx={{
                    height: 8,
                    backgroundColor: '#e0e0e0',
                    borderRadius: 1,
                    overflow: 'hidden',
                  }}
                >
                  <Box
                    sx={{
                      height: '100%',
                      width: `${(count / topology.totalCircuits) * 100}%`,
                      backgroundColor: CIRCUIT_COLORS[type],
                      transition: 'width 0.3s',
                    }}
                  />
                </Box>

                <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary' }}>
                  {((count / topology.totalCircuits) * 100).toFixed(1)}% of total
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Network diagram (simplified representation) */}
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Network Segments
      </Typography>

      <Paper sx={{ p: 3, mb: 3, backgroundColor: '#f5f5f5', borderRadius: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-around', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
          {/* Head Office */}
          <Box sx={{ textAlign: 'center' }}>
            <Paper sx={{ p: 2, backgroundColor: '#fff3e0', mb: 1, minWidth: 120 }}>
              <Typography sx={{ fontWeight: 600, fontSize: '0.9rem' }}>🏢 HQ</Typography>
            </Paper>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              Central Site
            </Typography>
          </Box>

          {/* Connections */}
          <Box sx={{ color: '#ccc', fontSize: '1.5rem' }}>↔️</Box>

          {/* Branch Offices */}
          <Box sx={{ textAlign: 'center' }}>
            <Paper sx={{ p: 2, backgroundColor: '#e3f2fd', mb: 1, minWidth: 120 }}>
              <Typography sx={{ fontWeight: 600, fontSize: '0.9rem' }}>🏢 Branches</Typography>
              <Typography variant="caption">×{Math.max(1, Math.ceil(topology.totalCircuits / 2))}</Typography>
            </Paper>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              Remote Sites
            </Typography>
          </Box>

          <Box sx={{ color: '#ccc', fontSize: '1.5rem' }}>↔️</Box>

          {/* Cloud */}
          <Box sx={{ textAlign: 'center' }}>
            <Paper sx={{ p: 2, backgroundColor: '#e8f5e9', mb: 1, minWidth: 120 }}>
              <Typography sx={{ fontWeight: 600, fontSize: '0.9rem' }}>☁️ Cloud</Typography>
            </Paper>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              Cloud Services
            </Typography>
          </Box>
        </Box>
      </Paper>

      {/* Circuit details table */}
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Circuit Details
      </Typography>

      <TableContainer component={Paper} sx={{ maxHeight: 500 }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell sx={{ fontWeight: 600 }}>Circuit Name</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Type</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Bandwidth</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Description</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {circuits.map((circuit) => (
              <TableRow key={circuit.id} hover>
                <TableCell sx={{ fontWeight: 500 }}>{circuit.name}</TableCell>
                <TableCell>
                  <Chip
                    label={circuit.subtype || 'Unknown'}
                    size="small"
                    sx={{
                      backgroundColor: CIRCUIT_COLORS[circuit.subtype || 'unknown'],
                      color: 'white',
                    }}
                  />
                </TableCell>
                <TableCell sx={{ fontSize: '0.85rem' }}>
                  {circuit.attributes?.bandwidth || 'N/A'}
                </TableCell>
                <TableCell sx={{ fontSize: '0.85rem', color: 'text.secondary' }}>
                  {circuit.description?.substring(0, 40)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </ReportShell>
  );
}
