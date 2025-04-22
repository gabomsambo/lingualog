# LinguaLog

A journaling and diary app for language learners that tracks entries, analyzes writing growth, and gives AI feedback.

## Features

- **Language Learning Journal**: Write and track your language learning journey
- **Grammar Feedback**: Get AI-powered grammar corrections for your entries
- **Vocabulary Extraction**: Automatically extract and save important vocabulary from your entries
- **Writing Statistics**: Track your progress with visual statistics and analytics

## Tech Stack

- **Frontend**: Next.js 14 with App Router, Tailwind CSS, shadcn/ui
- **Backend**: Supabase (Authentication, Database, Storage)
- **AI Integration**: GPT-4o for grammar correction and vocabulary extraction
- **Deployment**: Vercel

## Getting Started

### Prerequisites

- Node.js 18+ installed
- Supabase account
- OpenAI API key

### Environment Setup

Create a `.env.local` file in the root directory with the following variables:

```
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
OPENAI_API_KEY=your_openai_api_key
```

### Installation

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/lingualog.git
   cd lingualog
   ```

2. Install dependencies
   ```bash
   npm install
   ```

3. Run the development server
   ```bash
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

## Database Setup

1. Set up a new Supabase project
2. Run the SQL migrations in the `supabase/migrations` folder
3. Set up authentication providers (Email, Google)

## Deployment

The application is set up for easy deployment on Vercel:

1. Connect your GitHub repository to Vercel
2. Set up the environment variables in the Vercel dashboard
3. Deploy!

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.