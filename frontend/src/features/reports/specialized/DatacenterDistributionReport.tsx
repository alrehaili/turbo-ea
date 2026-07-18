/**
 * Datacenter Distribution Report
 * Visualizes geographic distribution and deployment of datacenters and services
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

interface Location {
  id: string;
  name: string;
  type: 'region' | 'country' | 'city';
}

interface Datacenter {
  id: string;
  name: string;
  subtype?: string;
  description?: string;
  location_id?: string;
  attributes?: Record<string, any>;
}

interface DatacenterDist {
  location: Location;
  datacenters: Datacenter[];
  appCount: number;
  itComponentCount: number;
}

export default function DatacenterDistributionReport() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [datacenters, setDatacenters] = useState<Datacenter[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const dcResp = await api.get<{ data: Datacenter[] }>(
          '/cards?type=Datacenter&page_size=200'
        );
        const locResp = await api.get<{ data: Location[] }>(
          '/cards?type=Location&page_size=200'
        );

        setDatacenters(dcResp.data);
        setLocations(locResp.data);
        setLoading(false);
      } catch (err: any) {
        setError(err.detail || 'Failed to load datacenters');
        setLoading(false);
      }
    })();
  }, []);

  const grouped = useMemo(() => {
    const groups: Record<string, DatacenterDist> = {};

    datacenters.forEach((dc) => {
      const locId = dc.attributes?.location_id || 'unassigned';
      const location: Location =
        locations.find((l) => l.id === locId) || { id: locId, name: 'Unassigned', type: 'region' };

      if (!groups[locId]) {
        groups[locId] = { location, datacenters: [], appCount: 0, itComponentCount: 0 };
      }
      groups[locId].datacenters.push(dc);
    });

    return Object.values(groups).sort((a, b) => b.datacenters.length - a.datacenters.length);
  }, [datacenters, locations]);

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

  const SUBTYPE_COLORS: Record<string, string> = {
    onPremise: '#ff9800',
    cloudRegion: '#2196f3',
    edgeLocation: '#4caf50',
  };

  return (
    <ReportShell title="Datacenter Distribution" icon="dns" hasTableToggle={false}>
      {/* Summary stats */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="primary">
              {grouped.length}
            </Typography>
            <Typography variant="caption">Locations</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="primary">
              {datacenters.length}
            </Typography>
            <Typography variant="caption">Datacenters</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="success.main">
              {datacenters.filter((d) => d.subtype === 'cloudRegion').length}
            </Typography>
            <Typography variant="caption">Cloud Regions</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="warning.main">
              {datacenters.filter((d) => d.subtype === 'onPremise').length}
            </Typography>
            <Typography variant="caption">On-Premise</Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Location breakdown */}
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Deployment by Location
      </Typography>

      <Grid container spacing={2}>
        {grouped.map((dist) => (
          <Grid item xs={12} md={6} key={dist.location.id}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 1.5 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    📍 {dist.location.name}
                  </Typography>
                  <Chip
                    label={`${dist.datacenters.length} DCs`}
                    size="small"
                    color="primary"
                  />
                </Box>

                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
                  {dist.datacenters.map((dc) => (
                    <Chip
                      key={dc.id}
                      label={dc.name}
                      size="small"
                      sx={{
                        backgroundColor: SUBTYPE_COLORS[dc.subtype || 'onPremise'] || '#9e9e9e',
                        color: 'white',
                      }}
                    />
                  ))}
                </Box>

                <Grid container spacing={1}>
                  <Grid item xs={6}>
                    <Box sx={{ p: 1, backgroundColor: '#e3f2fd', borderRadius: 1, textAlign: 'center' }}>
                      <Typography variant="caption" sx={{ fontWeight: 500 }}>
                        {dist.datacenters.filter((d) => d.subtype === 'cloudRegion').length}
                      </Typography>
                      <Typography variant="caption" sx={{ display: 'block', fontSize: '0.7rem' }}>
                        Cloud
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box sx={{ p: 1, backgroundColor: '#fff3e0', borderRadius: 1, textAlign: 'center' }}>
                      <Typography variant="caption" sx={{ fontWeight: 500 }}>
                        {dist.datacenters.filter((d) => d.subtype === 'onPremise').length}
                      </Typography>
                      <Typography variant="caption" sx={{ display: 'block', fontSize: '0.7rem' }}>
                        On-Prem
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Details table */}
      <Typography variant="h6" sx={{ mt: 4, mb: 2, fontWeight: 600 }}>
        Datacenter Details
      </Typography>

      <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell sx={{ fontWeight: 600 }}>Datacenter</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Location</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Type</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Description</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {datacenters.map((dc) => {
              const loc = locations.find((l) => l.id === dc.attributes?.location_id);
              return (
                <TableRow key={dc.id} hover>
                  <TableCell>{dc.name}</TableCell>
                  <TableCell>{loc?.name || 'Unassigned'}</TableCell>
                  <TableCell>
                    <Chip
                      label={dc.subtype || 'unknown'}
                      size="small"
                      sx={{
                        backgroundColor: SUBTYPE_COLORS[dc.subtype || 'onPremise'] || '#9e9e9e',
                        color: 'white',
                      }}
                    />
                  </TableCell>
                  <TableCell sx={{ fontSize: '0.85rem', color: 'text.secondary' }}>
                    {dc.description?.substring(0, 50)}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </ReportShell>
  );
}
