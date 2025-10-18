/**
 * ResizableTable Class
 * Adds draggable column resizing to HTML tables with user-specific and screen-size-specific persistence
 */
class ResizableTable {
  constructor(tableElement) {
    this.table = tableElement;
    this.tableName = this.table.dataset.tableName;
    this.userId = document.body.dataset.userId;
    this.minWidth = 50; // Minimum column width in pixels

    // Screen size breakpoints (in pixels)
    this.breakpoints = {
      sm: 640,
      md: 768,
      lg: 1024
    };

    // Drag state
    this.currentHandle = null;
    this.currentColumn = null;
    this.startX = 0;
    this.startWidth = 0;

    // Current screen size
    this.currentScreenSize = this.getScreenSize();

    // Debounce timer for window resize
    this.resizeTimer = null;

    if (!this.tableName || !this.userId) {
      console.error('ResizableTable: Missing required data attributes (data-table-name or data-user-id)');
      return;
    }

    this.init();
  }

  /**
   * Initialize the resizable table
   */
  init() {
    this.addResizeHandles();
    this.loadColumnWidths();
    this.attachWindowResizeListener();
  }

  /**
   * Get current screen size category
   */
  getScreenSize() {
    const width = window.innerWidth;
    if (width < this.breakpoints.sm) return 'sm';
    if (width < this.breakpoints.md) return 'md';
    if (width < this.breakpoints.lg) return 'lg';
    return 'xl';
  }

  /**
   * Add resize handles to table headers (except last column)
   */
  addResizeHandles() {
    const headers = this.table.querySelectorAll('thead th');

    headers.forEach((header, index) => {
      // Don't add handle to the last column
      if (index < headers.length - 1) {
        const handle = document.createElement('div');
        handle.className = 'resize-handle';
        handle.dataset.columnIndex = index;

        // Attach event listeners
        handle.addEventListener('mousedown', (e) => this.onMouseDown(e, header, index));

        header.appendChild(handle);
      }
    });
  }

  /**
   * Handle mouse down on resize handle
   */
  onMouseDown(e, column, columnIndex) {
    e.preventDefault();

    this.currentHandle = e.target;
    this.currentColumn = column;
    this.currentColumnIndex = columnIndex;
    this.startX = e.pageX;
    this.startWidth = column.offsetWidth;

    // Add visual feedback
    this.currentHandle.classList.add('active');
    this.table.classList.add('resizing');

    // Attach global mouse move and mouse up listeners
    document.addEventListener('mousemove', this.onMouseMove);
    document.addEventListener('mouseup', this.onMouseUp);
  }

  /**
   * Handle mouse move during resize
   */
  onMouseMove = (e) => {
    if (!this.currentColumn) return;

    const diff = e.pageX - this.startX;
    let newWidth = Math.max(this.minWidth, this.startWidth + diff);

    // Prevent table from exceeding container width
    const container = this.table.parentElement;
    const currentTableWidth = this.table.offsetWidth;
    const currentColumnWidth = this.currentColumn.offsetWidth;
    const widthDifference = newWidth - currentColumnWidth;
    const projectedTableWidth = currentTableWidth + widthDifference;

    // If the new width would make the table overflow the container, cap it
    if (projectedTableWidth > container.offsetWidth) {
      const maxAllowedWidth = newWidth - (projectedTableWidth - container.offsetWidth);
      newWidth = Math.max(this.minWidth, maxAllowedWidth);
    }

    this.setColumnWidth(this.currentColumnIndex, newWidth);
  }

  /**
   * Handle mouse up to end resize
   */
  onMouseUp = () => {
    if (!this.currentColumn) return;

    // Remove visual feedback
    if (this.currentHandle) {
      this.currentHandle.classList.remove('active');
    }
    this.table.classList.remove('resizing');

    // Save the new widths
    this.saveColumnWidths();

    // Reset state
    this.currentHandle = null;
    this.currentColumn = null;
    this.currentColumnIndex = null;

    // Remove global listeners
    document.removeEventListener('mousemove', this.onMouseMove);
    document.removeEventListener('mouseup', this.onMouseUp);
  }

  /**
   * Set width for a specific column using colgroup
   */
  setColumnWidth(columnIndex, width) {
    const cols = this.table.querySelectorAll('colgroup col');
    if (cols[columnIndex]) {
      cols[columnIndex].style.width = `${width}px`;
    }
  }

  /**
   * Get localStorage key for current table/user/screen size
   */
  getStorageKey() {
    return `table_widths_${this.tableName}_${this.userId}_${this.currentScreenSize}`;
  }

  /**
   * Save current column widths to localStorage
   */
  saveColumnWidths() {
    const cols = this.table.querySelectorAll('colgroup col');
    const widths = {};

    cols.forEach((col) => {
      const columnName = col.dataset.column;
      if (columnName) {
        // Get the actual computed width from the corresponding header
        const header = this.table.querySelector(`thead th[data-column="${columnName}"]`);
        const width = header ? header.offsetWidth : null;
        if (width) {
          widths[columnName] = width;
        }
      }
    });

    try {
      localStorage.setItem(this.getStorageKey(), JSON.stringify(widths));
    } catch (e) {
      console.error('Failed to save column widths:', e);
    }
  }

  /**
   * Load column widths from localStorage and apply them
   */
  loadColumnWidths() {
    try {
      const savedWidths = localStorage.getItem(this.getStorageKey());
      if (!savedWidths) return;

      const widths = JSON.parse(savedWidths);
      const cols = this.table.querySelectorAll('colgroup col');

      cols.forEach((col, index) => {
        const columnName = col.dataset.column;
        if (columnName && widths[columnName]) {
          this.setColumnWidth(index, widths[columnName]);
        }
      });
    } catch (e) {
      console.error('Failed to load column widths:', e);
    }
  }

  /**
   * Reset column widths to defaults
   */
  reset() {
    try {
      localStorage.removeItem(this.getStorageKey());

      // Remove inline styles from colgroup cols
      const cols = this.table.querySelectorAll('colgroup col');
      cols.forEach(col => {
        col.style.width = '';
      });

      // Reload the page to show defaults
      window.location.reload();
    } catch (e) {
      console.error('Failed to reset column widths:', e);
    }
  }

  /**
   * Attach window resize listener with debouncing
   * Only triggers when screen size category changes
   */
  attachWindowResizeListener() {
    window.addEventListener('resize', () => {
      // Clear existing timer
      if (this.resizeTimer) {
        clearTimeout(this.resizeTimer);
      }

      // Set new timer (250ms debounce)
      this.resizeTimer = setTimeout(() => {
        const newScreenSize = this.getScreenSize();

        // Only reload if screen size category changed
        if (newScreenSize !== this.currentScreenSize) {
          this.currentScreenSize = newScreenSize;
          this.loadColumnWidths();
        }
      }, 250);
    });
  }
}

/**
 * Initialize all resizable tables on page load
 */
document.addEventListener('DOMContentLoaded', () => {
  const resizableTables = document.querySelectorAll('.resizable-table');

  resizableTables.forEach(table => {
    // Create instance for each table (stores instance on element for later access)
    table.resizableInstance = new ResizableTable(table);
  });
});

/**
 * Global reset function for reset buttons
 * Usage: onclick="resetTableWidths('table-name')"
 */
function resetTableWidths(tableName) {
  const table = document.querySelector(`[data-table-name="${tableName}"]`);
  if (table && table.resizableInstance) {
    table.resizableInstance.reset();
  }
}
