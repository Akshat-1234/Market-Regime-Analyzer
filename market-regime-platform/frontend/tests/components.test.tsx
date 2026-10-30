import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { WorkspaceContext } from '../src/context';
import { DataTable, DateRange } from '../src/components/Common';
import type { Workspace } from '../src/types';

describe('interactive data components',()=>{
  it('sets a date preset against the actual data boundary',()=>{
    const setStart=vi.fn(),setEnd=vi.fn();
    const ctx={info:{metadata:{first_return_date:'2012-01-05',last_return_date:'2026-10-22'}},start:'2012-01-05',end:'2026-10-22',setStart,setEnd} as unknown as Workspace;
    render(<WorkspaceContext.Provider value={ctx}><DateRange/></WorkspaceContext.Provider>);
    fireEvent.click(screen.getByRole('button',{name:'1Y'}));
    expect(setEnd).toHaveBeenCalledWith('2026-10-22');expect(setStart).toHaveBeenCalledWith('2025-10-22');
  });
  it('sorts real rows and expands the table',()=>{
    render(<DataTable filename="x.csv" initialRows={1} rows={[{name:'B',value:3},{name:'A',value:2}]} columns={[{key:'name',label:'NAME'},{key:'value',label:'VALUE'}]}/>);
    expect(screen.getByText('B')).toBeInTheDocument();expect(screen.queryByText('A')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:/NAME/}));expect(screen.getByText('A')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:/Show all 2 rows/}));expect(screen.getByText('B')).toBeInTheDocument();
  });
});
