import { useState } from 'react'
import { Heading } from '../components/heading'
import {
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableHeader,
  TableCell,
} from '../components/table'
import { Button } from '../components/button'
import {
  Dialog,
  DialogTitle,
  DialogDescription,
  DialogActions,
  DialogBody,
} from '../components/dialog'
import { deleteTenant } from '../api/client'
import { useTenant } from '../contexts/TenantContext'
import type { TenantResponse } from '../types/api'

export function AdminPage() {
  const { tenants, removeTenant } = useTenant()
  const [pendingDelete, setPendingDelete] = useState<TenantResponse | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDeleteClick = (tenant: TenantResponse) => {
    setError(null)
    setPendingDelete(tenant)
  }

  const handleConfirm = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    setError(null)
    try {
      await deleteTenant(pendingDelete.id)
      removeTenant(pendingDelete.id)
      setPendingDelete(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete tenant')
    } finally {
      setDeleting(false)
    }
  }

  const handleCancel = () => {
    if (deleting) return
    setPendingDelete(null)
    setError(null)
  }

  return (
    <div>
      <Heading className="font-heading">Admin</Heading>
      <div className="mt-6">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>Name</TableHeader>
              <TableHeader>Industry</TableHeader>
              <TableHeader>Created</TableHeader>
              <TableHeader></TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {tenants.map((tenant) => (
              <TableRow key={tenant.id}>
                <TableCell>{tenant.name}</TableCell>
                <TableCell>{tenant.industry}</TableCell>
                <TableCell>
                  {new Date(tenant.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <Button color="red" onClick={() => handleDeleteClick(tenant)}>
                    Delete
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={pendingDelete !== null} onClose={handleCancel}>
        <DialogTitle>Delete tenant</DialogTitle>
        <DialogDescription>
          Are you sure you want to delete <strong>{pendingDelete?.name}</strong>? This action cannot
          be undone and will remove all associated data.
        </DialogDescription>
        {error && (
          <DialogBody>
            <p className="text-sm text-red-600">{error}</p>
          </DialogBody>
        )}
        <DialogActions>
          <Button outline onClick={handleCancel} disabled={deleting}>
            Cancel
          </Button>
          <Button color="red" onClick={handleConfirm} disabled={deleting}>
            {deleting ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  )
}
