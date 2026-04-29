# PDF AI Assistant

A modern, premium SaaS application for extracting insights from PDFs using AI. Built with Next.js 16, React 19, and a sleek 3-panel interface inspired by Notion, Linear, and Vercel.

## Features

✨ **Core Capabilities**
- **PDF Upload**: Drag-and-drop interface with instant file processing
- **AI Chat**: Ask questions about your documents and get instant answers
- **Visual Evidence**: See highlighted pages that contain supporting information
- **Session Management**: Unique session IDs for maintaining conversation context
- **Real-time Processing**: Streaming responses with loading indicators

🎨 **UI/UX**
- **3-Panel Layout**: Document panel (left) → Chat (center) → Evidence viewer (right)
- **Premium Design**: Modern spacing, subtle shadows, smooth transitions (150-250ms)
- **Dark/Light Mode**: Full theme support with oklch color system
- **Responsive**: Clean, professional interface matching Vercel/Linear aesthetic

🚀 **Technical Stack**
- **Frontend**: Next.js 16 (App Router), React 19, JavaScript
- **Styling**: Tailwind CSS 4 with design tokens
- **UI Components**: shadcn/ui components
- **Icons**: Lucide React
- **State**: React Hooks (useState, useRef, useEffect)
- **HTTP**: Fetch API for backend communication

## Getting Started

### Prerequisites

- Node.js 18+ and pnpm
- Python backend service running (see Backend Setup below)

### Installation

1. **Install Dependencies**
   ```bash
   pnpm install
   ```

2. **Run Development Server**
   ```bash
   pnpm dev
   ```
   
   Open [http://localhost:3000](http://localhost:3000) in your browser.

3. **Start Backend Service**
   
   In a separate terminal, ensure your Python backend is running on `http://localhost:8000` with the required endpoints.

## Backend API Integration

### Environment Variables

Create a `.env.local` file (optional, APIs are local by default):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### API Endpoints

#### 1. Upload PDF
```
POST /upload-pdf
Content-Type: multipart/form-data

Request:
  file: <PDF file>

Response:
{
  "file_hash": "abc123...",
  "message": "PDF processed successfully",
  "chunks": 24
}
```

#### 2. Ask Question
```
POST /ask
Content-Type: application/json

Request:
{
  "session_id": "uuid-string",
  "file_hash": "abc123...",
  "query": "What is the main topic?"
}

Response:
{
  "answer": "The document discusses...",
  "highlights": ["page 1", "page 3"],
  "images": [
    {
      "page": 1,
      "types": ["direct"],
      "image_path": "output/hash/page_1.png"
    },
    {
      "page": 3,
      "types": ["evidence"],
      "image_path": "output/hash/page_3.png"
    }
  ]
}
```

## Architecture

### Component Structure

```
app/
├── page.jsx                 # Main app container & state management
├── layout.tsx              # Root layout with metadata
└── globals.css             # Design tokens & theme

components/
├── DocumentPanel.jsx       # Left sidebar - file upload & info
├── ChatPanel.jsx          # Center - AI chat interface
├── ViewerPanel.jsx        # Right - PDF image viewer
└── ui/                    # shadcn/ui components
```

### State Management

The app uses React hooks for state:

```javascript
- fileHash          // Hash of uploaded PDF
- sessionId         // Unique session UUID
- messages          // Array of chat messages
- images            // Array of PDF images with highlights
- loading           // Loading state for API calls
- fileName          // Name of uploaded file
- processingStatus  // Upload/processing status
```

### Data Flow

```
Upload PDF
  ↓
File → FormData → POST /upload-pdf → fileHash + status
  ↓
User Question
  ↓
Query → POST /ask (with fileHash, sessionId)
  ↓
Response → Messages + Images
  ↓
Display in Chat & Viewer
```

## Design System

### Colors

The app uses an oklch-based color system with semantic tokens:

- **Primary**: Main brand color for buttons and accents
- **Secondary**: Supporting color
- **Muted**: Disabled/secondary text
- **Destructive**: Error and warning states
- **Background/Foreground**: Text and background colors
- **Card**: Elevated surface color

### Typography

- **Sans**: Geist font family
- **Mono**: Geist Mono for code
- **Line Height**: 1.4-1.6 for body text (leading-relaxed)

### Spacing & Radius

- **Spacing**: Tailwind scale (4px, 8px, 12px, 16px, etc.)
- **Border Radius**: 10px (0.625rem) standard, with variants

### Animations

- **Duration**: 150-250ms transitions
- **Easing**: Smooth, natural motion
- **Loading**: Bounce and spin animations for indicators

## Features Breakdown

### 📄 Document Panel

- Drag-and-drop file upload
- File metadata display (name, hash, status)
- Processing status indicator
- Quick tips section
- Supports drag hover state

### 💬 Chat Panel

- User messages (right-aligned, primary color)
- Assistant responses (left-aligned, card style)
- Loading indicator with bounce animation
- Typing animation support
- Empty state guidance
- Auto-scroll to latest message
- Keyboard shortcuts (Enter to send)

### 👁️ Evidence Viewer

- Displays PDF page images
- Page navigation with prev/next buttons
- Highlight type badges (direct/evidence)
- Color-coded highlights (green/orange)
- Highlight legend
- Image error handling
- Smooth page transitions

## Development

### Adding New Components

1. Create component in `components/`
2. Use shadcn/ui components for consistency
3. Follow naming convention: PascalCase.jsx
4. Export as default

### Styling

- Use Tailwind utility classes
- Reference design tokens via CSS variables
- Keep component-specific styles minimal
- Use `cn()` utility for conditional classes

### Backend Development

The frontend expects specific response formats. Ensure your backend:

1. Returns valid JSON with proper content-type headers
2. Provides file_hash on PDF upload
3. Returns answer, highlights, and images array on queries
4. Handles errors gracefully with appropriate HTTP status codes

## Building for Production

```bash
# Build the app
pnpm build

# Start production server
pnpm start
```

## Performance Optimizations

- ✅ Image lazy loading in viewer
- ✅ Message virtualization for long conversations
- ✅ Efficient state updates with React hooks
- ✅ CSS animations over JavaScript animations
- ✅ Optimized bundle with Next.js 16 + Turbopack

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Requires JavaScript enabled
- Supports both light and dark modes

## License

MIT

## Support

For issues or questions:
1. Check the backend API is running on localhost:8000
2. Verify file format is valid PDF
3. Check browser console for error messages
4. Ensure CORS is enabled on backend if running on different origin

---

Built with ❤️ using Next.js, React, and Tailwind CSS
